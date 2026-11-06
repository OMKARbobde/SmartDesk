import secrets
from collections.abc import Mapping
from datetime import timedelta

from django.db import IntegrityError, OperationalError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from auditlog.services import (
    record_bulk_ticket_update,
    record_ticket_archived,
    record_ticket_changes,
    record_ticket_created,
    record_ticket_restored,
)
from smartdesk.api import Conflict
from .models import Ticket


_PUBLIC_ID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_PUBLIC_ID_ATTEMPTS = 5


def generate_public_ticket_id():
    """Generate a 20-character-or-shorter opaque public ticket identifier."""
    suffix = "".join(secrets.choice(_PUBLIC_ID_ALPHABET) for _ in range(17))
    return f"SD-{suffix}"


def create_ticket(*, created_by, **values):
    """Create a ticket, retrying only when the unique public ID collides."""
    for _ in range(_PUBLIC_ID_ATTEMPTS):
        ticket_id = generate_public_ticket_id()
        try:
            with transaction.atomic():
                ticket = Ticket.objects.create(
                    ticket_id=ticket_id,
                    created_by=created_by,
                    **values,
                )
                record_ticket_created(actor=created_by, ticket=ticket)
                return ticket
        except IntegrityError:
            # The database unique constraint resolves simultaneous ID races.
            # An inner atomic block keeps the surrounding request transaction usable.
            if not Ticket.objects.filter(ticket_id=ticket_id).exists():
                raise
        except OperationalError as exc:
            if "locked" not in str(exc).lower() and "busy" not in str(exc).lower():
                raise
    raise Conflict("The ticket could not be created during concurrent database activity. Retry the request.")


def _handle_sqlite_lock(exc):
    if "locked" in str(exc).lower() or "busy" in str(exc).lower():
        raise Conflict("The ticket changed during this request. Refresh and retry.") from exc
    raise exc


def _next_updated_at(previous):
    """Return a timestamp strictly later than the persisted value."""
    current = timezone.now()
    if current <= previous:
        return previous + timedelta(microseconds=1)
    return current


def update_ticket_if_unchanged(ticket, *, actor, **changes):
    """Compare-and-update a ticket to avoid overwriting a concurrent write."""
    before = {
        "status": ticket.status,
        "priority": ticket.priority,
        "department_id": ticket.department_id,
        "title": ticket.title,
        "description": ticket.description,
    }
    updates = dict(changes)
    updates["updated_at"] = _next_updated_at(ticket.updated_at)
    try:
        with transaction.atomic():
            updated = Ticket.objects.filter(
                pk=ticket.pk,
                updated_at=ticket.updated_at,
                status=ticket.status,
            ).update(**updates)
            if updated != 1:
                raise Conflict("The ticket changed during this request. Refresh and retry.")
            ticket.refresh_from_db()
            record_ticket_changes(actor=actor, ticket=ticket, before=before)
    except OperationalError as exc:
        _handle_sqlite_lock(exc)
    ticket.refresh_from_db()
    return ticket


def _set_ticket_archive_state(ticket, *, is_archived, actor=None):
    """Conditionally transition archive state; repeated requests are no-ops."""
    currently_archived = not is_archived
    updates = {
        "is_archived": is_archived,
        "archived_at": timezone.now() if is_archived else None,
        "archived_by_id": actor.pk if is_archived else None,
        "updated_at": _next_updated_at(ticket.updated_at),
    }
    try:
        with transaction.atomic():
            changed = Ticket.objects.filter(
                pk=ticket.pk,
                updated_at=ticket.updated_at,
                is_archived=currently_archived,
            ).update(**updates)
            if changed != 1:
                ticket.refresh_from_db()
                if ticket.is_archived == is_archived:
                    return ticket
                raise Conflict("The ticket changed during this request. Refresh and retry.")
            if is_archived:
                record_ticket_archived(actor=actor, ticket=ticket)
            else:
                record_ticket_restored(actor=actor, ticket=ticket)
    except OperationalError as exc:
        _handle_sqlite_lock(exc)
    ticket.refresh_from_db()
    return ticket


def archive_ticket(ticket, *, actor):
    """Archive a ticket without deleting it or any related records."""
    if ticket.is_archived:
        ticket.refresh_from_db()
        if ticket.is_archived:
            return ticket
    return _set_ticket_archive_state(ticket, is_archived=True, actor=actor)


def restore_ticket(ticket, *, actor):
    """Restore an archived ticket; repeated restores are idempotent."""
    if not ticket.is_archived:
        ticket.refresh_from_db()
        if not ticket.is_archived:
            return ticket
    return _set_ticket_archive_state(ticket, is_archived=False, actor=actor)


def _conditional_bulk_update(ticket, *, field, value):
    return Ticket.objects.filter(
        pk=ticket.pk,
        updated_at=ticket.updated_at,
        status=ticket.status,
    ).update(**{field: value, "updated_at": _next_updated_at(ticket.updated_at)})


def apply_bulk_ticket_update(tickets, *, field, value, actor):
    """Atomically apply one validated field change to all supplied tickets."""
    try:
        with transaction.atomic():
            for ticket in tickets:
                previous_value = getattr(ticket, field)
                updated = _conditional_bulk_update(ticket, field=field, value=value)
                if updated != 1:
                    raise Conflict("A ticket changed during this request. No tickets were updated.")
                record_bulk_ticket_update(
                    actor=actor,
                    ticket=ticket,
                    field=field,
                    previous_value=previous_value,
                    new_value=value,
                )
    except OperationalError as exc:
        _handle_sqlite_lock(exc)
    return list(Ticket.objects.filter(pk__in=[ticket.pk for ticket in tickets]).order_by("pk"))


def validate_ticket_payload_fields(data, allowed_fields):
    """Reject unknown and server-managed input instead of silently ignoring it."""
    if not isinstance(data, Mapping):
        raise ValidationError({
            "non_field_errors": ["Expected a JSON object."]
        })
    unknown = set(data) - set(allowed_fields)
    if unknown:
        raise ValidationError({
            field: ["This field is not writable."]
            for field in sorted(unknown)
        })
