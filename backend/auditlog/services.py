from .models import AuditEvent


_TICKET_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}
_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
_ASSIGNMENT_STATUSES = {"ASSIGNED", "ACCEPTED", "COMPLETED", "REASSIGNED"}
_GENERIC_TICKET_FIELDS = {"title", "description", "department_id"}


def _positive_id(value, field_name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _validate_details(event_type, details):
    if not isinstance(details, dict):
        raise ValueError("Audit details must be an object.")

    if event_type == "TICKET_CREATED":
        if set(details) != {"status", "priority", "department_id"}:
            raise ValueError("Ticket creation audit fields are invalid.")
        if details["status"] not in _TICKET_STATUSES or details["priority"] not in _PRIORITIES:
            raise ValueError("Ticket creation audit values are invalid.")
        department_id = details["department_id"]
        if department_id is not None:
            _positive_id(department_id, "department_id")
    elif event_type in {
        "TICKET_STATUS_CHANGED", "TICKET_BULK_STATUS_CHANGED",
        "TICKET_PRIORITY_CHANGED", "TICKET_BULK_PRIORITY_CHANGED",
        "ASSIGNMENT_ACCEPTED", "ASSIGNMENT_COMPLETED",
    }:
        if set(details) != {"from", "to"}:
            raise ValueError("Audit transition fields are invalid.")
        if event_type in {"TICKET_STATUS_CHANGED", "TICKET_BULK_STATUS_CHANGED"}:
            allowed = _TICKET_STATUSES
        elif event_type in {"TICKET_PRIORITY_CHANGED", "TICKET_BULK_PRIORITY_CHANGED"}:
            allowed = _PRIORITIES
        elif event_type == "ASSIGNMENT_ACCEPTED":
            allowed = {"ASSIGNED", "ACCEPTED"}
        else:
            allowed = {"ACCEPTED", "COMPLETED"}
        if details["from"] not in allowed or details["to"] not in allowed:
            raise ValueError("Audit transition values are invalid.")
    elif event_type == "TICKET_UPDATED":
        if set(details) != {"changed_fields", "changes"}:
            raise ValueError("Ticket update audit fields are invalid.")
        fields = details["changed_fields"]
        changes = details["changes"]
        if not isinstance(fields, list) or not fields or set(fields) - _GENERIC_TICKET_FIELDS:
            raise ValueError("Ticket update audit changed_fields are invalid.")
        if not isinstance(changes, dict) or set(changes) - {"department_id"}:
            raise ValueError("Ticket update audit changes are invalid.")
        if "department_id" in changes:
            transition = changes["department_id"]
            if not isinstance(transition, dict) or set(transition) != {"from", "to"}:
                raise ValueError("Department audit transition is invalid.")
            for value in transition.values():
                if value is not None:
                    _positive_id(value, "department_id")
    elif event_type == "ASSIGNMENT_CREATED":
        if set(details) != {"assignment_status", "assigned_to_profile_id"}:
            raise ValueError("Assignment creation audit fields are invalid.")
        if details["assignment_status"] != "ASSIGNED":
            raise ValueError("Assignment creation status is invalid.")
        _positive_id(details["assigned_to_profile_id"], "assigned_to_profile_id")
    elif event_type == "ASSIGNMENT_REASSIGNED":
        required = {
            "previous_assignment_id", "previous_assignee_profile_id",
            "previous_assignee_user_id", "assigned_to_profile_id",
        }
        if set(details) != required:
            raise ValueError("Assignment reassignment audit fields are invalid.")
        for field_name, value in details.items():
            _positive_id(value, field_name)
    elif event_type in {"TICKET_ARCHIVED", "TICKET_RESTORED"}:
        if set(details) != {"from", "to"}:
            raise ValueError("Ticket archive audit fields are invalid.")
        expected = (False, True) if event_type == "TICKET_ARCHIVED" else (True, False)
        if (details["from"], details["to"]) != expected:
            raise ValueError("Ticket archive audit values are invalid.")
    else:
        raise ValueError("Unsupported audit event type.")

    return details


def record_event(*, actor, event_type, details, ticket=None, assignment=None, target_user=None):
    """Create one safe audit event; callers must include it in their transaction."""
    if actor is None or not getattr(actor, "is_authenticated", False):
        raise ValueError("Audit events require an authenticated actor.")
    _validate_details(event_type, details)
    if assignment is not None and ticket is None:
        ticket = assignment.ticket

    return AuditEvent.objects.create(
        actor=actor,
        actor_user_id_snapshot=actor.pk,
        event_type=event_type,
        ticket=ticket,
        ticket_pk_snapshot=ticket.pk if ticket else None,
        ticket_public_id_snapshot=ticket.ticket_id if ticket else None,
        assignment=assignment,
        assignment_pk_snapshot=assignment.pk if assignment else None,
        target_user=target_user,
        target_user_id_snapshot=target_user.pk if target_user else None,
        details=details,
    )


def record_ticket_created(*, actor, ticket):
    return record_event(
        actor=actor,
        event_type="TICKET_CREATED",
        ticket=ticket,
        details={
            "status": ticket.status,
            "priority": ticket.priority,
            "department_id": ticket.department_id,
        },
    )


def record_ticket_changes(*, actor, ticket, before):
    after = {
        "status": ticket.status,
        "priority": ticket.priority,
        "department_id": ticket.department_id,
        "title": ticket.title,
        "description": ticket.description,
    }
    if before["status"] != after["status"]:
        record_event(
            actor=actor,
            event_type="TICKET_STATUS_CHANGED",
            ticket=ticket,
            details={"from": before["status"], "to": after["status"]},
        )
    if before["priority"] != after["priority"]:
        record_event(
            actor=actor,
            event_type="TICKET_PRIORITY_CHANGED",
            ticket=ticket,
            details={"from": before["priority"], "to": after["priority"]},
        )

    changed_fields = [
        field for field in ("title", "description", "department_id")
        if before[field] != after[field]
    ]
    if changed_fields:
        changes = {}
        if "department_id" in changed_fields:
            changes["department_id"] = {
                "from": before["department_id"],
                "to": after["department_id"],
            }
        record_event(
            actor=actor,
            event_type="TICKET_UPDATED",
            ticket=ticket,
            details={"changed_fields": changed_fields, "changes": changes},
        )


def record_bulk_ticket_update(*, actor, ticket, field, previous_value, new_value):
    if previous_value == new_value:
        return None
    event_type = {
        "status": "TICKET_BULK_STATUS_CHANGED",
        "priority": "TICKET_BULK_PRIORITY_CHANGED",
    }.get(field)
    if event_type is None:
        raise ValueError("Unsupported bulk ticket audit field.")
    return record_event(
        actor=actor,
        event_type=event_type,
        ticket=ticket,
        details={"from": previous_value, "to": new_value},
    )


def record_ticket_archived(*, actor, ticket):
    return record_event(
        actor=actor,
        event_type="TICKET_ARCHIVED",
        ticket=ticket,
        details={"from": False, "to": True},
    )


def record_ticket_restored(*, actor, ticket):
    return record_event(
        actor=actor,
        event_type="TICKET_RESTORED",
        ticket=ticket,
        details={"from": True, "to": False},
    )


def record_assignment_created(*, actor, assignment):
    return record_event(
        actor=actor,
        event_type="ASSIGNMENT_CREATED",
        ticket=assignment.ticket,
        assignment=assignment,
        target_user=assignment.assigned_to.user,
        details={
            "assignment_status": assignment.status,
            "assigned_to_profile_id": assignment.assigned_to_id,
        },
    )


def record_assignment_reassigned(*, actor, previous, assignment):
    return record_event(
        actor=actor,
        event_type="ASSIGNMENT_REASSIGNED",
        ticket=assignment.ticket,
        assignment=assignment,
        target_user=assignment.assigned_to.user,
        details={
            "previous_assignment_id": previous.pk,
            "previous_assignee_profile_id": previous.assigned_to_id,
            "previous_assignee_user_id": previous.assigned_to.user_id,
            "assigned_to_profile_id": assignment.assigned_to_id,
        },
    )


def record_assignment_status_change(*, actor, assignment, previous_status):
    event_type = {
        "ACCEPTED": "ASSIGNMENT_ACCEPTED",
        "COMPLETED": "ASSIGNMENT_COMPLETED",
    }.get(assignment.status)
    if event_type is None:
        return None
    return record_event(
        actor=actor,
        event_type=event_type,
        ticket=assignment.ticket,
        assignment=assignment,
        target_user=assignment.assigned_to.user,
        details={"from": previous_status, "to": assignment.status},
    )
