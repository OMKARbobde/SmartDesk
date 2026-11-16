from rest_framework import serializers
from smartdesk.api import Conflict

from .models import Department


class DepartmentReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name", "code", "description", "is_active", "created_at")


class DepartmentWriteSerializer(serializers.ModelSerializer):
    # Explicit fields avoid DRF's default UniqueValidator turning uniqueness
    # conflicts into 400s; the API convention uses a 409 conflict response.
    name = serializers.CharField(max_length=100)
    code = serializers.CharField(max_length=10)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = Department
        fields = ("name", "code", "description", "is_active")

    def validate(self, attrs):
        for field in ("name", "code"):
            value = attrs.get(field)
            if value is None:
                continue
            matches = Department.objects.filter(**{field: value})
            if self.instance is not None:
                matches = matches.exclude(pk=self.instance.pk)
            if matches.exists():
                raise Conflict(f"A department with this {field} already exists.")
        return attrs
