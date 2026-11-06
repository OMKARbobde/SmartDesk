from django.db.models import Count, Q

from departments.models import Department


STATUS_VALUES = ("OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED")
PRIORITY_VALUES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
RESOLUTION_TIME_UNAVAILABLE_REASON = (
    "Tickets do not store a resolved_at timestamp or status history; updated_at "
    "cannot reliably identify when a ticket was resolved."
)


def _count_expressions():
    expressions = {"total_tickets": Count("id", distinct=True)}
    expressions.update({
        f"status_{value.lower()}": Count("id", filter=Q(status=value), distinct=True)
        for value in STATUS_VALUES
    })
    expressions.update({
        f"priority_{value.lower()}": Count("id", filter=Q(priority=value), distinct=True)
        for value in PRIORITY_VALUES
    })
    return expressions


def _counts_from_aggregate(values):
    status_counts = {
        value: values.get(f"status_{value.lower()}", 0) or 0
        for value in STATUS_VALUES
    }
    priority_counts = {
        value: values.get(f"priority_{value.lower()}", 0) or 0
        for value in PRIORITY_VALUES
    }
    return {
        "total_tickets": values.get("total_tickets", 0) or 0,
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "workload_count": status_counts["OPEN"] + status_counts["IN_PROGRESS"],
        "average_resolution_time_seconds": None,
        "resolution_time_available": False,
        "resolution_time_unavailable_reason": RESOLUTION_TIME_UNAVAILABLE_REASON,
    }


def department_analytics(*, tickets, department_id=None):
    """Aggregate visible, already-filtered ticket rows by their department."""
    aggregate_fields = _count_expressions()
    summary = _counts_from_aggregate(tickets.aggregate(**aggregate_fields))
    grouped = list(
        tickets.values("department_id", "department__name", "department__code")
        .annotate(**aggregate_fields)
    )

    department_queryset = Department.objects.filter(is_active=True).order_by("name", "id")
    if department_id is not None:
        department_queryset = department_queryset.filter(pk=department_id)

    rows_by_id = {}
    for department in department_queryset:
        rows_by_id[department.pk] = {
            "department": {
                "id": department.pk,
                "name": department.name,
                "code": department.code,
            },
            **_counts_from_aggregate({}),
        }

    for values in grouped:
        department_id_value = values["department_id"]
        department = None
        if department_id_value is not None:
            department = {
                "id": department_id_value,
                "name": values["department__name"],
                "code": values["department__code"],
            }
        rows_by_id[department_id_value] = {
            "department": department,
            **_counts_from_aggregate(values),
        }

    if department_id is not None:
        rows_by_id = {
            key: value for key, value in rows_by_id.items()
            if key == department_id
        }

    rows = sorted(
        rows_by_id.values(),
        key=lambda row: (
            row["department"]["name"].casefold() if row["department"] else "unassigned",
            row["department"]["id"] if row["department"] else 0,
        ),
    )
    return {"summary": summary, "departments": rows}
