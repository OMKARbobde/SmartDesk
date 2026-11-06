from math import ceil

from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from smartdesk.api import success_response
from .models import AuditEvent
from .serializers import AuditEventReadSerializer


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
EVENT_TYPES = {value for value, _ in AuditEvent.EVENT_TYPES}
ORDERING_FIELDS = {"created_at", "event_type", "id"}
ALLOWED_QUERY_PARAMETERS = {
    "event_type", "actor", "ticket", "created_after", "created_before",
    "ordering", "page", "page_size",
}


def _one(query, key, default=None):
    values = query.getlist(key)
    if len(values) > 1:
        raise ValidationError({key: ["Provide this parameter once."]})
    return values[0] if values else default


def _positive_integer(raw, field):
    if raw is None or not raw.isdigit() or int(raw) < 1:
        raise ValidationError({field: ["Use a positive integer."]})
    return int(raw)


def _timestamp(query, field):
    raw = _one(query, field)
    if raw is None:
        return None
    value = parse_datetime(raw)
    if value is None or value.utcoffset() is None:
        raise ValidationError({field: ["Use an ISO 8601 timestamp with a timezone offset."]})
    return value


class AuditEventListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        query = request.query_params
        unsupported = set(query.keys()) - ALLOWED_QUERY_PARAMETERS
        if unsupported:
            raise ValidationError({key: ["Unsupported query parameter."] for key in sorted(unsupported)})

        page_raw = _one(query, "page", "1")
        page_size_raw = _one(query, "page_size", str(DEFAULT_PAGE_SIZE))
        try:
            page, page_size = int(page_raw), int(page_size_raw)
        except (TypeError, ValueError):
            raise ValidationError({"pagination": ["Page and page_size must be integers."]})
        if page < 1:
            raise ValidationError({"page": ["Page numbering starts at 1."]})
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValidationError({"page_size": [f"Use a value from 1 to {MAX_PAGE_SIZE}."]})

        queryset = AuditEvent.objects.select_related(
            "actor", "ticket", "assignment", "target_user"
        )
        event_type = _one(query, "event_type")
        if event_type is not None:
            if event_type not in EVENT_TYPES:
                raise ValidationError({"event_type": ["Select a valid event type."]})
            queryset = queryset.filter(event_type=event_type)

        actor = _one(query, "actor")
        if actor is not None:
            queryset = queryset.filter(actor_user_id_snapshot=_positive_integer(actor, "actor"))

        ticket = _one(query, "ticket")
        if ticket is not None:
            queryset = queryset.filter(ticket_pk_snapshot=_positive_integer(ticket, "ticket"))

        created_after = _timestamp(query, "created_after")
        created_before = _timestamp(query, "created_before")
        if created_after and created_before and created_after >= created_before:
            raise ValidationError({"created_before": ["Must be later than created_after."]})
        if created_after:
            queryset = queryset.filter(created_at__gte=created_after)
        if created_before:
            queryset = queryset.filter(created_at__lt=created_before)

        ordering = _one(query, "ordering", "-created_at")
        ordering_field = ordering[1:] if ordering.startswith("-") else ordering
        if ordering_field not in ORDERING_FIELDS:
            raise ValidationError({"ordering": ["This ordering field is not supported."]})

        count = queryset.count()
        sort = f"-{ordering_field}" if ordering.startswith("-") else ordering_field
        queryset = queryset.order_by(sort, "id")
        total_pages = ceil(count / page_size) if count else 0
        rows = queryset[(page - 1) * page_size:page * page_size] if page <= total_pages else []
        return success_response(AuditEventReadSerializer(rows, many=True).data, meta={"pagination": {
            "count": count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "next": page + 1 if page < total_pages else None,
            "previous": page - 1 if 1 < page <= total_pages else None,
        }})
