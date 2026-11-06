from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ImmutableAuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Audit events are immutable.")

    def delete(self):
        raise ValidationError("Audit events cannot be deleted.")


class ImmutableAuditManager(models.Manager.from_queryset(ImmutableAuditQuerySet)):
    pass


class AuditEvent(models.Model):
    objects = ImmutableAuditManager()

    EVENT_TYPES = (
        ("TICKET_CREATED", "Ticket created"),
        ("TICKET_UPDATED", "Ticket updated"),
        ("TICKET_STATUS_CHANGED", "Ticket status changed"),
        ("TICKET_PRIORITY_CHANGED", "Ticket priority changed"),
        ("TICKET_BULK_STATUS_CHANGED", "Ticket status changed in bulk"),
        ("TICKET_BULK_PRIORITY_CHANGED", "Ticket priority changed in bulk"),
        ("ASSIGNMENT_CREATED", "Assignment created"),
        ("ASSIGNMENT_REASSIGNED", "Assignment reassigned"),
        ("ASSIGNMENT_ACCEPTED", "Assignment accepted"),
        ("ASSIGNMENT_COMPLETED", "Assignment completed"),
        ("TICKET_ARCHIVED", "Ticket archived"),
        ("TICKET_RESTORED", "Ticket restored"),
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events_created",
    )
    actor_user_id_snapshot = models.PositiveBigIntegerField(db_index=True)
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES, db_index=True)
    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    ticket_pk_snapshot = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    ticket_public_id_snapshot = models.CharField(max_length=20, null=True, blank=True)
    assignment = models.ForeignKey(
        "assignment.Assignment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    assignment_pk_snapshot = models.PositiveBigIntegerField(null=True, blank=True)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events_as_target",
    )
    target_user_id_snapshot = models.PositiveBigIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "id")

    def __str__(self):
        return f"{self.event_type} #{self.pk}"

    def save(self, *args, **kwargs):
        if self.pk is not None and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit events are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events cannot be deleted.")
