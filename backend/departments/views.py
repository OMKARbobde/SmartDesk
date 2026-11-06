from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from accounts.permissions import IsSmartDeskUser
from smartdesk.api import success_response
from .models import Department
from .serializers import DepartmentReadSerializer


class DepartmentListView(APIView):
    permission_classes = [IsSmartDeskUser]

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
