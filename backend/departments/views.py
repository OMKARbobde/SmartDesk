from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsSmartDeskUser
from auditlog.services import record_department_changes, record_department_created
from smartdesk.api import Conflict, success_response
from .models import Department
from .serializers import DepartmentReadSerializer, DepartmentWriteSerializer


class DepartmentListView(APIView):
    permission_classes = [IsSmartDeskUser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return super().get_permissions()

    def get(self, request):
        unknown = set(request.query_params.keys()) - {"include_inactive"}
        if unknown:
            raise ValidationError({key: ["Unsupported query parameter."] for key in sorted(unknown)})
        values = request.query_params.getlist("include_inactive")
        if len(values) > 1 or (values and values[0] not in {"true", "false"}):
            raise ValidationError({"include_inactive": ["Use true or false once."]})
        include_inactive = bool(values and values[0] == "true")
        if include_inactive and request.user.role != "ADMIN":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        departments = Department.objects.all()
        if not include_inactive:
            departments = departments.filter(is_active=True)
        departments = departments.order_by("name", "id")
        return success_response(DepartmentReadSerializer(departments, many=True).data)

    def post(self, request):
        serializer = DepartmentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                department = serializer.save()
                record_department_created(
                    actor=request.user,
                    department=department,
                    changed_fields=serializer.validated_data.keys(),
                )
        except IntegrityError as exc:
            raise Conflict("A department with this name or code already exists.") from exc
        return success_response(
            DepartmentReadSerializer(department).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": reverse("department-detail", args=(department.pk,), request=request)},
        )


class DepartmentDetailView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            with transaction.atomic():
                department = get_object_or_404(Department, pk=pk)
                serializer = DepartmentWriteSerializer(department, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                if not serializer.validated_data:
                    raise ValidationError({"non_field_errors": ["Provide at least one writable field."]})
                before = {
                    "name": department.name,
                    "code": department.code,
                    "description": department.description,
                    "is_active": department.is_active,
                }
                department = serializer.save()
                record_department_changes(actor=request.user, department=department, before=before)
        except IntegrityError as exc:
            raise Conflict("A department with this name or code already exists.") from exc
        return success_response(DepartmentReadSerializer(department).data)
