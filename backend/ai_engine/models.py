
from django.db import models
from tickets.models import Ticket


class TicketAnalysis(models.Model):

    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.CASCADE,
        related_name='ai_analysis'
    )

    predicted_category = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    predicted_priority = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    sentiment = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    confidence_score = models.FloatField(
        null=True,
        blank=True
    )

    suggested_response = models.TextField(
        blank=True,
        null=True
    )

    analyzed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AI Analysis - {self.ticket}"
