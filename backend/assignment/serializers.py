from collections.abc import Mapping

from rest_framework import serializers

from accounts.models import EmployeeProfile
from .models import Assignment


def validate_object_payload(data, allowed):
    if not isinstance(data, Mapping):
        raise serializers.ValidationError({"non_field_errors": ["Expected a JSON object."]})
    unknown = set(data) - set(allowed)
    if unknown:
        raise serializers.ValidationError({key: ["This field is not writable."] for key in sorted(unknown)})


class AssignmentCreateSerializer(serializers.Serializer):
    employee_profile_id = serializers.PrimaryKeyRelatedField(
        source="assigned_to", queryset=EmployeeProfile.objects.select_related("user", "department")
    )
    remarks = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def to_internal_value(self, data):
        validate_object_payload(data, self.fields)
        return super().to_internal_value(data)

    def validate_assigned_to(self, profile):
        if not profile.is_available or not profile.user.is_active:
            raise serializers.ValidationError("Employee is unavailable for new assignments.")
        if not profile.department.is_active:
            raise serializers.ValidationError("Employee belongs to an inactive department.")
        return profile


class AssignmentUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Assignment.ASSIGNMENT_STATUS, required=False)
    remarks = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def to_internal_value(self, data):
        user = self.context["request"].user
        allowed = {"status"} if user.role == "EMPLOYEE" else set(self.fields)
        validate_object_payload(data, allowed)
        return super().to_internal_value(data)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError({"non_field_errors": ["Provide at least one writable field."]})
        if "status" in attrs:
            allowed = {"ASSIGNED": "ACCEPTED", "ACCEPTED": "COMPLETED"}
            if allowed.get(self.instance.status) != attrs["status"]:
                raise serializers.ValidationError({"status": [
                    f"Transition from {self.instance.status} to {attrs['status']} is not permitted."
                ]})
        return attrs


class AssignmentReadSerializer(serializers.ModelSerializer):
    ticket_id = serializers.IntegerField(source="ticket.id", read_only=True)
    public_ticket_id = serializers.CharField(source="ticket.ticket_id", read_only=True)
    assigned_to = serializers.SerializerMethodField()
    assigned_by = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = ("id", "ticket_id", "public_ticket_id", "assigned_to", "assigned_by",
                  "status", "assigned_at", "remarks")

    @staticmethod
    def get_assigned_to(obj):
        user = obj.assigned_to.user
        return {"employee_profile_id": obj.assigned_to_id,
                "employee_id": obj.assigned_to.employee_id,
                "display_name": user.get_full_name().strip() or user.username}

    @staticmethod
    def get_assigned_by(obj):
        user = obj.assigned_by
        if user is None:
            return None
        return {"id": user.pk, "display_name": user.get_full_name().strip() or user.username}
