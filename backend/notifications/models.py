from django.conf import settings
from django.db import models


class Notification(models.Model):
    TYPE_CHOICES = (
        ("ASSIGNMENT_CREATED", "Assignment created"),
        ("ASSIGNMENT_REASSIGNED", "Assignment reassigned"),
        ("TICKET_STATUS_CHANGED", "Ticket status changed"),
        ("ASSIGNMENT_ACCEPTED", "Assignment accepted"),
        ("ASSIGNMENT_COMPLETED", "Assignment completed"),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=32, choices=TYPE_CHOICES, db_index=True)
    title = models.CharField(max_length=200)
    message = models.CharField(max_length=500)
    related_ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    related_assignment = models.ForeignKey(
        "assignment.Assignment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    event_key = models.CharField(max_length=120, unique=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"{self.notification_type} for user #{self.recipient_id}"
