from math import ceil

from django.db.models import Q
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsAdminOrAgent, IsSmartDeskUser
from smartdesk.api import Conflict, success_response
from .models import Ticket
from .permissions import (
    TicketVisibilityPermission,
    can_transition_ticket_status,
    visible_tickets_for,
)
from .serializers import (
    BulkTicketActionSerializer,
    TicketCreateSerializer,
    TicketReadSerializer,
    TicketUpdateSerializer,
    ticket_queryset,
)
from .services import (
    apply_bulk_ticket_update,
    archive_ticket,
    create_ticket,
    restore_ticket,
    update_ticket_if_unchanged,
)


PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
ORDERING_FIELDS = {"created_at", "updated_at", "ticket_id", "status", "priority", "id"}
LIST_QUERY_PARAMETERS = {
    "search", "status", "priority", "department", "created_after", "created_before",
    "ordering", "page", "page_size",
}


def _single_query_value(query, key, default=None):
    values = query.getlist(key)
    if len(values) > 1:
        raise ValidationError({key: ["Provide this parameter once; use comma-separated values where supported."]})
    return values[0] if values else default


def _csv_values(query, key, allowed_values):
    raw = _single_query_value(query, key)
    if raw is None:
        return None
    values = [item.strip() for item in raw.split(",")]
    if not values or any(not item for item in values):
        raise ValidationError({key: ["Provide one or more comma-separated values."]})
    if len(values) != len(set(values)) or any(item not in allowed_values for item in values):
        raise ValidationError({key: ["One or more values are invalid."]})
    return values


def _parse_timestamp(query, key):
    raw = _single_query_value(query, key)
    if raw is None:
        return None
    value = parse_datetime(raw)
    if value is None or value.utcoffset() is None:
        raise ValidationError({key: ["Use an ISO 8601 timestamp with a timezone offset."]})
    return value


def _ticket_list_response(request, base_queryset):
    query = request.query_params
    unsupported = set(query.keys()) - LIST_QUERY_PARAMETERS
    if unsupported:
        raise ValidationError({
            key: ["Unsupported query parameter."] for key in sorted(unsupported)
        })

    page_raw = _single_query_value(query, "page", "1")
    page_size_raw = _single_query_value(query, "page_size", str(PAGE_SIZE_DEFAULT))
    try:
        page = int(page_raw)
        page_size = int(page_size_raw)
    except (TypeError, ValueError):
        raise ValidationError({"pagination": ["Page and page_size must be integers."]})
    if page < 1:
        raise ValidationError({"page": ["Page numbering starts at 1."]})
    if page_size < 1 or page_size > PAGE_SIZE_MAX:
        raise ValidationError({"page_size": [f"Use a value from 1 to {PAGE_SIZE_MAX}."]})

    ordering = _single_query_value(query, "ordering", "-created_at")
    ordering_field = ordering[1:] if ordering.startswith("-") else ordering
    if ordering_field not in ORDERING_FIELDS:
        raise ValidationError({"ordering": ["This ordering field is not supported."]})

    statuses = _csv_values(query, "status", {value for value, _ in Ticket.STATUS_CHOICES})
    priorities = _csv_values(query, "priority", {value for value, _ in Ticket.PRIORITY_CHOICES})
    departments = _single_query_value(query, "department")
    department_ids = None
    if departments is not None:
        department_parts = [part.strip() for part in departments.split(",")]
        if not department_parts or any(not part.isdigit() or int(part) < 1 for part in department_parts):
            raise ValidationError({"department": ["Use one or more comma-separated department IDs."]})
        department_ids = [int(part) for part in department_parts]
        if len(department_ids) != len(set(department_ids)):
            raise ValidationError({"department": ["Department IDs must be unique."]})

    created_after = _parse_timestamp(query, "created_after")
    created_before = _parse_timestamp(query, "created_before")
    if created_after and created_before and created_after >= created_before:
        raise ValidationError({"created_before": ["Must be later than created_after."]})

    # Visibility and archive scope are established before search, filters,
    # counts, and pagination.
    queryset = ticket_queryset(base_queryset)
    search = (_single_query_value(query, "search", "") or "").strip()
    if search:
        queryset = queryset.filter(
            Q(ticket_id__icontains=search)
            | Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(created_by__username__icontains=search)
            | Q(created_by__first_name__icontains=search)
            | Q(created_by__last_name__icontains=search)
            | Q(created_by__email__icontains=search)
            | Q(department__name__icontains=search)
        )
    if statuses:
        queryset = queryset.filter(status__in=statuses)
    if priorities:
        queryset = queryset.filter(priority__in=priorities)
    if department_ids is not None:
        queryset = queryset.filter(department_id__in=department_ids)
    if created_after:
        queryset = queryset.filter(created_at__gte=created_after)
    if created_before:
        queryset = queryset.filter(created_at__lt=created_before)

    count = queryset.distinct().count()
    sort = f"-{ordering_field}" if ordering.startswith("-") else ordering_field
    ordered = queryset.distinct().order_by(sort, "id")
    start = (page - 1) * page_size
    total_pages = ceil(count / page_size) if count else 0
    tickets = list(ordered[start:start + page_size]) if page <= total_pages else []
    return success_response(
        TicketReadSerializer(tickets, many=True).data,
        meta={"pagination": {
            "count": count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "next": page + 1 if page < total_pages else None,
            "previous": page - 1 if 1 < page <= total_pages else None,
        }},
    )


class TicketListCreateView(APIView):
    permission_classes = [IsSmartDeskUser]

    def get(self, request):
        return _ticket_list_response(
            request,
            visible_tickets_for(request.user).filter(is_archived=False),
        )

    def post(self, request):
        serializer = TicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        values.setdefault("priority", "MEDIUM")
        ticket = create_ticket(created_by=request.user, **values)
        location = reverse("ticket-detail", args=(ticket.pk,), request=request)
        return success_response(
            TicketReadSerializer(ticket).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": location},
        )


class TicketDetailView(APIView):
    permission_classes = [IsSmartDeskUser, TicketVisibilityPermission]

    def get_queryset(self):
        include_archived = self.request.user.role == "ADMIN"
        return ticket_queryset(visible_tickets_for(
            self.request.user,
            include_archived=include_archived,
        ))

    def get_object(self, pk):
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(self.request, instance)
        return instance

    def get(self, request, pk):
        return success_response(TicketReadSerializer(self.get_object(pk)).data)

    def patch(self, request, pk):
        ticket = self.get_object(pk)
        serializer = TicketUpdateSerializer(
            ticket,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        changes = dict(serializer.validated_data)
        expected_updated_at = changes.pop("expected_updated_at", None)
        if not changes:
            raise ValidationError({"non_field_errors": ["Provide at least one writable field."]})
        if expected_updated_at is not None and expected_updated_at != ticket.updated_at:
            raise Conflict("The ticket changed since it was loaded. Refresh and retry.")

        new_status = changes.get("status")
        if new_status is not None and not can_transition_ticket_status(request.user, ticket, new_status):
            raise ValidationError({"status": [
                f"Transition from {ticket.status} to {new_status} is not permitted for this role."
            ]})

        updated = update_ticket_if_unchanged(ticket, actor=request.user, **changes)
        return success_response(TicketReadSerializer(updated).data)


class TicketBulkActionView(APIView):
    permission_classes = [IsAdminOrAgent]

    def post(self, request):
        serializer = BulkTicketActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        queryset = visible_tickets_for(request.user).filter(is_archived=False)
        tickets_by_id = {
            ticket.pk: ticket
            for ticket in ticket_queryset(queryset.filter(pk__in=values["ticket_ids"])).order_by("pk")
        }
        if set(tickets_by_id) != set(values["ticket_ids"]):
            raise NotFound("One or more tickets were not found.")
        tickets = [tickets_by_id[pk] for pk in sorted(values["ticket_ids"])]
        field = values["field"]
        value = values["value"]

        if field == "status":
            invalid = [
                ticket.ticket_id
                for ticket in tickets
                if not can_transition_ticket_status(request.user, ticket, value)
            ]
            if invalid:
                raise ValidationError({"status": [
                    "The requested transition is not permitted for every selected ticket."
                ]})

        updated = apply_bulk_ticket_update(tickets, field=field, value=value, actor=request.user)
        return success_response(TicketReadSerializer(updated, many=True).data)


class ArchivedTicketListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = visible_tickets_for(request.user, include_archived=True).filter(is_archived=True)
        return _ticket_list_response(request, queryset)


class TicketArchiveView(APIView):
    permission_classes = [IsAdminOrAgent]

    def post(self, request, pk):
        ticket = get_object_or_404(
            visible_tickets_for(request.user, include_archived=True),
            pk=pk,
        )
        archived = archive_ticket(ticket, actor=request.user)
        return success_response(TicketReadSerializer(archived).data)


class TicketRestoreView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        ticket = get_object_or_404(
            visible_tickets_for(request.user, include_archived=True),
            pk=pk,
        )
        restored = restore_ticket(ticket, actor=request.user)
        return success_response(TicketReadSerializer(restored).data)
