from rest_framework import serializers

from .models import Department


class DepartmentReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name", "code", "description", "is_active", "created_at")
