from .models import Notification


_STATUS_LABELS = {
    "OPEN": "Open",
    "IN_PROGRESS": "In Progress",
    "RESOLVED": "Resolved",
    "CLOSED": "Closed",
}


def _eligible_recipients(users, actor):
    recipients = {}
    actor_id = getattr(actor, "pk", None)
    for user in users:
        if user and user.is_active and user.pk != actor_id:
            recipients[user.pk] = user
    return recipients.values()


def _create_notification(*, recipient, event_key, notification_type, title, message, ticket=None, assignment=None):
    notification, _created = Notification.objects.get_or_create(
        event_key=event_key,
        defaults={
            "recipient": recipient,
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "related_ticket": ticket,
            "related_assignment": assignment,
        },
    )
    return notification


def notify_assignment_created(*, assignment, actor):
    """Notify the new assignee once for the created assignment."""
    ticket = assignment.ticket
    for recipient in _eligible_recipients((assignment.assigned_to.user,), actor):
        _create_notification(
            recipient=recipient,
            event_key=f"assignment-created:{assignment.pk}:{recipient.pk}",
            notification_type="ASSIGNMENT_CREATED",
            title="New ticket assignment",
            message=f"Ticket {ticket.ticket_id} has been assigned to you.",
            ticket=ticket,
            assignment=assignment,
        )


def notify_assignment_reassigned(*, previous, assignment, actor):
    """Notify the new assignee and the employee whose assignment ended."""
    ticket = assignment.ticket
    new_user = assignment.assigned_to.user
    previous_user = previous.assigned_to.user
    for recipient in _eligible_recipients((new_user, previous_user), actor):
        is_new_assignee = recipient.pk == new_user.pk
        _create_notification(
            recipient=recipient,
            event_key=f"assignment-reassigned:{assignment.pk}:{recipient.pk}",
            notification_type="ASSIGNMENT_REASSIGNED",
            title="Ticket reassigned to you" if is_new_assignee else "Ticket reassigned",
            message=(
                f"Ticket {ticket.ticket_id} has been assigned to you."
                if is_new_assignee
                else f"Your assignment for ticket {ticket.ticket_id} was reassigned."
            ),
            ticket=ticket,
            assignment=assignment,
        )


def notify_ticket_status_changed(*, ticket, actor, previous_status):
    if previous_status == ticket.status:
        return
    from assignment.models import Assignment

    recipients = [ticket.created_by]
    current = Assignment.objects.filter(
        ticket_id=ticket.pk,
        status__in=("ASSIGNED", "ACCEPTED"),
    ).select_related("assigned_to__user").first()
    if current:
        recipients.append(current.assigned_to.user)

    stamp = ticket.updated_at.isoformat()
    for recipient in _eligible_recipients(recipients, actor):
        _create_notification(
            recipient=recipient,
            event_key=f"ticket-status:{ticket.pk}:{stamp}:{recipient.pk}",
            notification_type="TICKET_STATUS_CHANGED",
            title="Ticket status changed",
            message=(
                f"Ticket {ticket.ticket_id} changed from "
                f"{_STATUS_LABELS.get(previous_status, previous_status)} to "
                f"{_STATUS_LABELS.get(ticket.status, ticket.status)}."
            ),
            ticket=ticket,
        )


def notify_assignment_status_changed(*, assignment, actor, previous_status):
    if assignment.status == previous_status:
        return
    notification_type = {
        "ACCEPTED": "ASSIGNMENT_ACCEPTED",
        "COMPLETED": "ASSIGNMENT_COMPLETED",
    }.get(assignment.status)
    if notification_type is None:
        return

    ticket = assignment.ticket
    verb = "accepted" if assignment.status == "ACCEPTED" else "completed"
    recipients = (ticket.created_by, assignment.assigned_by)
    for recipient in _eligible_recipients(recipients, actor):
        _create_notification(
            recipient=recipient,
            event_key=f"assignment-status:{assignment.pk}:{assignment.status}:{recipient.pk}",
            notification_type=notification_type,
            title=f"Assignment {verb}",
            message=f"The assignment for ticket {ticket.ticket_id} was {verb}.",
            ticket=ticket,
            assignment=assignment,
        )
