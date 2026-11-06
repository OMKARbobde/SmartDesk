from collections.abc import Mapping

from rest_framework import serializers

from departments.models import Department
from assignment.models import Assignment
from .models import EmployeeProfile


class EmployeeReadSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    display_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    department = serializers.SerializerMethodField()
    active_assignment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = ("id", "employee_id", "user_id", "display_name", "email", "role",
                  "department", "designation", "phone_number", "is_available", "joined_at",
                  "active_assignment_count")

    @staticmethod
    def get_display_name(obj):
        full_name = obj.user.get_full_name().strip()
        return full_name or obj.user.username

    @staticmethod
    def get_department(obj):
        return {"id": obj.department_id, "name": obj.department.name, "code": obj.department.code}


class EmployeeUpdateSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    is_available = serializers.BooleanField(required=False)
    designation = serializers.CharField(max_length=100, required=False)
    department_id = serializers.PrimaryKeyRelatedField(
        source="department", queryset=Department.objects.all(), required=False
    )

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError({"non_field_errors": ["Expected a JSON object."]})
        owner = self.context["is_owner"]
        allowed = {"phone_number"} if owner else set(self.fields)
        unknown = set(data) - allowed
        if unknown:
            raise serializers.ValidationError({key: ["This field is not writable."] for key in sorted(unknown)})
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save(update_fields=list(validated_data))
        return instance
