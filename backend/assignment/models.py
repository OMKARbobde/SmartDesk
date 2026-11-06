from django.db import models
from django.conf import settings


class Assignment(models.Model):

    ASSIGNMENT_STATUS = [
        ('ASSIGNED', 'Assigned'),
        ('ACCEPTED', 'Accepted'),
        ('COMPLETED', 'Completed'),
        ('REASSIGNED', 'Reassigned'),
    ]

    ticket = models.ForeignKey(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        related_name='assignments'
    )

    assigned_to = models.ForeignKey(
        'accounts.EmployeeProfile',
        on_delete=models.CASCADE,
        related_name='assigned_tickets'
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ticket_assignments_made'
    )

    status = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_STATUS,
        default='ASSIGNED'
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.ticket.ticket_id} - {self.assigned_to.employee_id}"