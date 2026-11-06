from django.db.models import Prefetch
from rest_framework import serializers

from assignment.models import Assignment
from departments.models import Department
from .models import Ticket
from .services import validate_ticket_payload_fields


CURRENT_ASSIGNMENT_STATUSES = ("ASSIGNED", "ACCEPTED")


class TicketReadSerializer(serializers.ModelSerializer):
    requester = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    assignee = serializers.SerializerMethodField()
    assignment_id = serializers.SerializerMethodField()
    is_archived = serializers.SerializerMethodField()
    archived_at = serializers.SerializerMethodField()
    archived_by = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = (
            "id",
            "ticket_id",
            "title",
            "description",
            "requester",
            "department",
            "status",
            "priority",
            "is_archived",
            "archived_at",
            "archived_by",
            "assignee",
            "assignment_id",
            "created_at",
            "updated_at",
        )

    @staticmethod
    def get_requester(obj):
        full_name = obj.created_by.get_full_name().strip()
        return {
            "id": obj.created_by_id,
            "display_name": full_name or obj.created_by.username,
            "email": obj.created_by.email,
        }

    @staticmethod
    def get_department(obj):
        if obj.department_id is None:
            return None
        return {
            "id": obj.department_id,
            "name": obj.department.name,
            "code": obj.department.code,
        }

    @staticmethod
    def _current_assignment(obj):
        prefetched = getattr(obj, "current_assignments", None)
        if prefetched is not None:
            return prefetched[0] if prefetched else None
        return (
            obj.assignments.filter(status__in=CURRENT_ASSIGNMENT_STATUSES)
            .select_related("assigned_to__user")
            .order_by("-assigned_at", "-pk")
            .first()
        )

    def get_assignee(self, obj):
        assignment = self._current_assignment(obj)
        if assignment is None:
            return None
        user = assignment.assigned_to.user
        full_name = user.get_full_name().strip()
        return {
            "employee_profile_id": assignment.assigned_to_id,
            "employee_id": assignment.assigned_to.employee_id,
            "display_name": full_name or user.username,
        }

    def get_assignment_id(self, obj):
        assignment = self._current_assignment(obj)
        return assignment.pk if assignment else None

    @staticmethod
    def get_is_archived(obj):
        return obj.is_archived

    @staticmethod
    def get_archived_at(obj):
        return obj.archived_at

    @staticmethod
    def get_archived_by(obj):
        user = obj.archived_by
        if user is None:
            return None
        full_name = user.get_full_name().strip()
        return {
            "id": user.pk,
            "display_name": full_name or user.username,
        }


class TicketCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.all(),
        allow_null=True,
        required=False,
    )
    priority = serializers.ChoiceField(choices=Ticket.PRIORITY_CHOICES, required=False)

    def to_internal_value(self, data):
        validate_ticket_payload_fields(data, self.fields)
        return super().to_internal_value(data)


class TicketUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False)
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.all(),
        allow_null=True,
        required=False,
    )
    status = serializers.ChoiceField(choices=Ticket.STATUS_CHOICES, required=False)
    priority = serializers.ChoiceField(choices=Ticket.PRIORITY_CHOICES, required=False)
    expected_updated_at = serializers.DateTimeField(required=True, write_only=True)

    def to_internal_value(self, data):
        user = self.context["request"].user
        if user.role == "EMPLOYEE":
            allowed = {"title", "description", "status", "expected_updated_at"}
        else:
            allowed = set(self.fields)
        validate_ticket_payload_fields(data, allowed)
        return super().to_internal_value(data)

    def validate(self, attrs):
        if "expected_updated_at" not in attrs:
            raise serializers.ValidationError({
                "expected_updated_at": ["This field is required for ticket updates."]
            })
        return attrs


class BulkTicketActionSerializer(serializers.Serializer):
    ticket_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    action = serializers.ChoiceField(choices=("set_status", "set_priority"))
    value = serializers.CharField()

    def to_internal_value(self, data):
        validate_ticket_payload_fields(data, self.fields)
        return super().to_internal_value(data)

    def validate_ticket_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Ticket IDs must be unique.")
        return value

    def validate(self, attrs):
        action, value = attrs["action"], attrs["value"]
        choices = dict(Ticket.STATUS_CHOICES if action == "set_status" else Ticket.PRIORITY_CHOICES)
        if value not in choices:
            field = "status" if action == "set_status" else "priority"
            raise serializers.ValidationError({field: ["Select a valid choice."]})
        attrs["field"] = "status" if action == "set_status" else "priority"
        return attrs


def ticket_queryset(queryset=None):
    queryset = queryset if queryset is not None else Ticket.objects.all()
    return queryset.select_related(
        "created_by",
        "department",
        "archived_by",
    ).prefetch_related(
        Prefetch(
            "assignments",
            queryset=Assignment.objects.filter(
                status__in=CURRENT_ASSIGNMENT_STATUSES,
            ).select_related("assigned_to__user").order_by("-assigned_at", "-pk"),
            to_attr="current_assignments",
        ),
    )
