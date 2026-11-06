from math import ceil

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrAgent, IsSmartDeskUser
from smartdesk.api import success_response
from tickets.permissions import visible_tickets_for
from tickets.models import Ticket
from .models import Assignment
from .serializers import AssignmentCreateSerializer, AssignmentReadSerializer, AssignmentUpdateSerializer
from .services import CURRENT_STATUSES, assign_or_reassign, update_assignment_if_unchanged


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _one(query, key, default=None):
    values = query.getlist(key)
    if len(values) > 1:
        raise ValidationError({key: ["Provide this parameter once."]})
    return values[0] if values else default


class AssignmentListView(APIView):
    permission_classes = [IsSmartDeskUser]

    def get(self, request):
        query = request.query_params
        unsupported = set(query.keys()) - {"ticket", "status", "page", "page_size"}
        if unsupported:
            raise ValidationError({key: ["Unsupported query parameter."] for key in sorted(unsupported)})
        page_raw, size_raw = _one(query, "page", "1"), _one(query, "page_size", str(DEFAULT_PAGE_SIZE))
        try:
            page, page_size = int(page_raw), int(size_raw)
        except (TypeError, ValueError):
            raise ValidationError({"pagination": ["Page and page_size must be integers."]})
        if page < 1:
            raise ValidationError({"page": ["Page numbering starts at 1."]})
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValidationError({"page_size": [f"Use a value from 1 to {MAX_PAGE_SIZE}."]})

        # Actor scoping is applied before filters/counting/pagination.
        queryset = Assignment.objects.select_related(
            "ticket", "assigned_to__user", "assigned_by"
        )
        if request.user.role != "ADMIN":
            queryset = queryset.filter(ticket__is_archived=False)
        if request.user.role == "EMPLOYEE":
            queryset = queryset.filter(assigned_to__user=request.user)
        ticket = _one(query, "ticket")
        if ticket is not None:
            if not ticket.isdigit() or int(ticket) < 1:
                raise ValidationError({"ticket": ["Use a positive ticket database ID."]})
            queryset = queryset.filter(ticket_id=int(ticket))
        status_value = _one(query, "status")
        valid_statuses = {value for value, _ in Assignment.ASSIGNMENT_STATUS}
        if status_value is not None:
            statuses = [part.strip() for part in status_value.split(",")]
            if not statuses or any(item not in valid_statuses for item in statuses) or len(statuses) != len(set(statuses)):
                raise ValidationError({"status": ["One or more assignment statuses are invalid."]})
            queryset = queryset.filter(status__in=statuses)
        count = queryset.count()
        queryset = queryset.order_by("-assigned_at", "-id")
        total_pages = ceil(count / page_size) if count else 0
        rows = queryset[(page - 1) * page_size:page * page_size] if page <= total_pages else []
        return success_response(AssignmentReadSerializer(rows, many=True).data, meta={"pagination": {
            "count": count, "page": page, "page_size": page_size, "total_pages": total_pages,
            "next": page + 1 if page < total_pages else None,
            "previous": page - 1 if 1 < page <= total_pages else None,
        }})


class TicketAssignmentCreateView(APIView):
    permission_classes = [IsAdminOrAgent]

    def post(self, request, ticket_id):
        # Global roles are still explicitly scoped through the shared visibility policy.
        ticket = get_object_or_404(visible_tickets_for(request.user), pk=ticket_id)
        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = assign_or_reassign(
            ticket=ticket,
            employee=serializer.validated_data["assigned_to"],
            actor=request.user,
            remarks=serializer.validated_data.get("remarks"),
        )
        location = reverse("assignment-detail", args=(assignment.pk,), request=request)
        return success_response(
            AssignmentReadSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": location},
        )


class AssignmentDetailView(APIView):
    permission_classes = [IsSmartDeskUser]

    def _get_assignment(self, request, pk):
        assignment = get_object_or_404(
            Assignment.objects.select_related("ticket", "assigned_to__user", "assigned_by"), pk=pk
        )
        if not visible_tickets_for(request.user).filter(pk=assignment.ticket_id).exists():
            raise NotFound()
        is_owner = assignment.assigned_to.user_id == request.user.pk
        if request.user.role == "EMPLOYEE" and not is_owner:
            raise NotFound()
        return assignment, is_owner

    def patch(self, request, pk):
        assignment, is_owner = self._get_assignment(request, pk)
        if request.user.role == "EMPLOYEE":
            current_count = Assignment.objects.filter(
                ticket_id=assignment.ticket_id, status__in=CURRENT_STATUSES
            ).count()
            if not is_owner or assignment.status not in CURRENT_STATUSES or current_count != 1:
                raise NotFound()
        elif request.user.role not in {"ADMIN", "AGENT"}:
            raise PermissionDenied()
        serializer = AssignmentUpdateSerializer(
            assignment, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated = update_assignment_if_unchanged(assignment, actor=request.user, **serializer.validated_data)
        return success_response(AssignmentReadSerializer(updated).data)
