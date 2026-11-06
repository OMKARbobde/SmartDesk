from django.db import IntegrityError, OperationalError, transaction
from rest_framework.exceptions import ValidationError

from auditlog.services import (
    record_assignment_created,
    record_assignment_reassigned,
    record_assignment_status_change,
)
from smartdesk.api import Conflict
from tickets.models import Ticket
from .models import Assignment


CURRENT_STATUSES = ("ASSIGNED", "ACCEPTED")


def assign_or_reassign(*, ticket, employee, actor, remarks=None):
    """Atomically preserve prior assignment history and create the current row."""
    try:
        with transaction.atomic():
            # Backends with row-lock support serialize writers for this ticket.
            # SQLite ignores select_for_update; its write-lock errors are handled below.
            ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
            # Recheck eligibility inside the write transaction to avoid assigning
            # a profile that was disabled after request validation.
            employee = type(employee).objects.select_related("user", "department").get(pk=employee.pk)
            if not employee.is_available or not employee.user.is_active or not employee.department.is_active:
                raise ValidationError({"employee_profile_id": ["Employee is unavailable for new assignments."]})
            current = list(Assignment.objects.filter(ticket=ticket, status__in=CURRENT_STATUSES).order_by("pk"))
            if len(current) > 1:
                raise Conflict("The ticket has multiple current assignments and requires reconciliation.")
            previous = None
            if current:
                previous = current[0]
                changed = Assignment.objects.filter(pk=previous.pk, status=previous.status).update(status="REASSIGNED")
                if changed != 1:
                    raise Conflict("The assignment changed during this request. Refresh and retry.")
            assignment = Assignment.objects.create(
                ticket=ticket, assigned_to=employee, assigned_by=actor,
                status="ASSIGNED", remarks=remarks,
            )
            if previous is None:
                record_assignment_created(actor=actor, assignment=assignment)
            else:
                record_assignment_reassigned(actor=actor, previous=previous, assignment=assignment)
            return assignment
    except IntegrityError as exc:
        raise Conflict("The assignment conflicts with the current ticket state.") from exc
    except OperationalError as exc:
        if "locked" in str(exc).lower() or "busy" in str(exc).lower():
            raise Conflict("The assignment changed during this request. Refresh and retry.") from exc
        raise


def update_assignment_if_unchanged(assignment, *, actor, **changes):
    updates = dict(changes)
    previous_status = assignment.status
    filters = {"pk": assignment.pk, "status": assignment.status, "remarks": assignment.remarks}
    try:
        with transaction.atomic():
            if Assignment.objects.filter(**filters).update(**updates) != 1:
                raise Conflict("The assignment changed during this request. Refresh and retry.")
            assignment.refresh_from_db()
            if assignment.status != previous_status:
                record_assignment_status_change(
                    actor=actor,
                    assignment=assignment,
                    previous_status=previous_status,
                )
    except OperationalError as exc:
        if "locked" in str(exc).lower() or "busy" in str(exc).lower():
            raise Conflict("The assignment changed during this request. Refresh and retry.") from exc
        raise
    assignment.refresh_from_db()
    return assignment
