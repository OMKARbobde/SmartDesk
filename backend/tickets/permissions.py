from django.db.models import Q
from rest_framework.permissions import BasePermission

from .models import Ticket


CURRENT_ASSIGNMENT_STATUSES = ("ASSIGNED", "ACCEPTED")
GLOBAL_TICKET_ROLES = ("ADMIN", "AGENT")

AGENT_STATUS_TRANSITIONS = {
    "OPEN": {"IN_PROGRESS"},
    "IN_PROGRESS": {"OPEN", "RESOLVED"},
    "RESOLVED": {"IN_PROGRESS", "CLOSED"},
    "CLOSED": set(),
}


def visible_tickets_for(user, *, include_archived=False):
    """Return tickets visible to a user, excluding archives unless requested."""
    if not user or not user.is_authenticated:
        return Ticket.objects.none()

    if user.role in GLOBAL_TICKET_ROLES:
        queryset = Ticket.objects.all()
    elif user.role == "EMPLOYEE":
        queryset = Ticket.objects.filter(
            Q(created_by=user)
            | Q(
                assignments__assigned_to__user=user,
                assignments__status__in=CURRENT_ASSIGNMENT_STATUSES,
            )
        ).distinct()
    else:
        return Ticket.objects.none()

    return queryset if include_archived else queryset.filter(is_archived=False)


class TicketVisibilityPermission(BasePermission):
    """Object permission for future ticket endpoints; does not add CRUD."""

    def has_object_permission(self, request, view, obj):
        return visible_tickets_for(
            request.user,
            include_archived=getattr(request.user, "role", None) == "ADMIN",
        ).filter(pk=obj.pk).exists()


def can_transition_ticket_status(user, ticket, new_status):
    """Apply the approved role and relationship status-transition matrix."""
    current = ticket.status
    if new_status == current:
        return True

    if user.role == "ADMIN":
        return True
    if user.role == "AGENT":
        return new_status in AGENT_STATUS_TRANSITIONS.get(current, set())
    if user.role != "EMPLOYEE":
        return False

    is_creator = ticket.created_by_id == user.pk
    is_current_assignee = ticket.assignments.filter(
        assigned_to__user_id=user.pk,
        status__in=CURRENT_ASSIGNMENT_STATUSES,
    ).exists()

    creator_transitions = {
        "OPEN": {"CLOSED"},
        "RESOLVED": {"IN_PROGRESS"},
    }
    assignee_transitions = {
        "OPEN": {"IN_PROGRESS"},
        "IN_PROGRESS": {"RESOLVED"},
        "RESOLVED": {"IN_PROGRESS"},
    }

    permitted = set()
    if is_creator:
        permitted.update(creator_transitions.get(current, set()))
    if is_current_assignee:
        permitted.update(assignee_transitions.get(current, set()))
    return new_status in permitted
