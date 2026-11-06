from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from accounts.permissions import IsSmartDeskUser
from smartdesk.api import success_response
from tickets.permissions import visible_tickets_for
from .analytics import department_analytics


def _single_query_value(query, key):
    values = query.getlist(key)
    if len(values) > 1:
        raise ValidationError({key: ["Provide this parameter once."]})
    return values[0] if values else None


def _parse_timestamp(query, key):
    raw = _single_query_value(query, key)
    if raw is None:
        return None
    value = parse_datetime(raw)
    if value is None or value.utcoffset() is None:
        raise ValidationError({key: ["Use an ISO 8601 timestamp with a timezone offset."]})
    return value


class DepartmentAnalyticsView(APIView):
    permission_classes = [IsSmartDeskUser]

    def get(self, request):
        query = request.query_params
        unsupported = set(query.keys()) - {"department", "created_after", "created_before"}
        if unsupported:
            raise ValidationError({
                key: ["Unsupported query parameter."] for key in sorted(unsupported)
            })

        raw_department = _single_query_value(query, "department")
        department_id = None
        if raw_department is not None:
            if not raw_department.isdigit() or int(raw_department) < 1:
                raise ValidationError({"department": ["Use a positive department database ID."]})
            department_id = int(raw_department)

        created_after = _parse_timestamp(query, "created_after")
        created_before = _parse_timestamp(query, "created_before")
        if created_after and created_before and created_after >= created_before:
            raise ValidationError({"created_before": ["Must be later than created_after."]})

        # Apply role visibility and archive exclusion before filters or aggregation.
        tickets = visible_tickets_for(request.user).filter(is_archived=False)
        if department_id is not None:
            tickets = tickets.filter(department_id=department_id)
        if created_after:
            tickets = tickets.filter(created_at__gte=created_after)
        if created_before:
            tickets = tickets.filter(created_at__lt=created_before)

        result = department_analytics(tickets=tickets, department_id=department_id)
        result["filters"] = {
            "department_id": department_id,
            "created_after": created_after.isoformat() if created_after else None,
            "created_before": created_before.isoformat() if created_before else None,
        }
        result["membership_semantics"] = (
            "Ticket membership is based on created_at; status and priority are current values."
        )
        return success_response(result)
