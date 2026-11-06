from math import ceil

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.views import APIView

from .employee_serializers import EmployeeReadSerializer, EmployeeUpdateSerializer
from .models import EmployeeProfile
from .permissions import IsAdminOrAgent, IsSmartDeskUser
from smartdesk.api import success_response


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
LIST_PARAMS = {"search", "department", "page", "page_size", "ordering"}
ACTIVE_ASSIGNMENTS = ("ASSIGNED", "ACCEPTED")


def _one(query, key, default=None):
    values = query.getlist(key)
    if len(values) > 1:
        raise ValidationError({key: ["Provide this parameter once."]})
    return values[0] if values else default


def _employee_queryset():
    return EmployeeProfile.objects.select_related("user", "department").annotate(
        active_assignment_count=Count(
            "assigned_tickets", filter=Q(assigned_tickets__status__in=ACTIVE_ASSIGNMENTS), distinct=True
        )
    )


class EmployeeListView(APIView):
    permission_classes = [IsAdminOrAgent]

    def get(self, request):
        query = request.query_params
        unsupported = set(query.keys()) - LIST_PARAMS
        if unsupported:
            raise ValidationError({key: ["Unsupported query parameter."] for key in sorted(unsupported)})
        page_raw = _one(query, "page", "1")
        size_raw = _one(query, "page_size", str(DEFAULT_PAGE_SIZE))
        try:
            page, page_size = int(page_raw), int(size_raw)
        except (TypeError, ValueError):
            raise ValidationError({"pagination": ["Page and page_size must be integers."]})
        if page < 1:
            raise ValidationError({"page": ["Page numbering starts at 1."]})
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValidationError({"page_size": [f"Use a value from 1 to {MAX_PAGE_SIZE}."]})
        ordering = _one(query, "ordering", "employee_id")
        field = ordering.lstrip("-")
        if field not in {"employee_id", "designation", "joined_at", "id"}:
            raise ValidationError({"ordering": ["This ordering field is not supported."]})
        qs = _employee_queryset()
        search = (_one(query, "search", "") or "").strip()
        if search:
            qs = qs.filter(Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search)
                           | Q(user__username__icontains=search) | Q(employee_id__icontains=search)
                           | Q(designation__icontains=search) | Q(department__name__icontains=search))
        department = _one(query, "department")
        if department is not None:
            if not department.isdigit() or int(department) < 1:
                raise ValidationError({"department": ["Use a positive department ID."]})
            qs = qs.filter(department_id=int(department))
        count = qs.count()
        sort = f"-{field}" if ordering.startswith("-") else field
        qs = qs.order_by(sort, "id")
        total_pages = ceil(count / page_size) if count else 0
        rows = qs[(page - 1) * page_size:page * page_size] if page <= total_pages else []
        return success_response(EmployeeReadSerializer(rows, many=True).data, meta={"pagination": {
            "count": count, "page": page, "page_size": page_size, "total_pages": total_pages,
            "next": page + 1 if page < total_pages else None,
            "previous": page - 1 if 1 < page <= total_pages else None,
        }})


class EmployeeDetailView(APIView):
    permission_classes = [IsSmartDeskUser]

    def _get_profile(self, request, profile_pk):
        profile = get_object_or_404(_employee_queryset(), pk=profile_pk)
        owner = profile.user_id == request.user.pk
        if request.user.role not in {"ADMIN", "AGENT"} and not owner:
            raise PermissionDenied()
        return profile, owner

    def get(self, request, profile_pk):
        profile, _ = self._get_profile(request, profile_pk)
        return success_response(EmployeeReadSerializer(profile).data)

    def patch(self, request, profile_pk):
        profile, owner = self._get_profile(request, profile_pk)
        if request.user.role not in {"ADMIN", "EMPLOYEE"}:
            raise PermissionDenied()
        serializer = EmployeeUpdateSerializer(
            profile, data=request.data, partial=True,
            context={"is_owner": owner and request.user.role == "EMPLOYEE"},
        )
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data:
            raise ValidationError({"non_field_errors": ["Provide at least one writable field."]})
        profile = serializer.save()
        profile = _employee_queryset().get(pk=profile.pk)
        return success_response(EmployeeReadSerializer(profile).data)
