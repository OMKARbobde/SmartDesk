
from django.contrib import admin
from .models import TicketAnalysis


@admin.register(TicketAnalysis)
class TicketAnalysisAdmin(admin.ModelAdmin):

    list_display = (
        'ticket',
        'predicted_category',
        'predicted_priority',
        'sentiment',
        'confidence_score',
        'analyzed_at'
    )

    search_fields = (
        'ticket__ticket_id',
        'ticket__title',
        'predicted_category'
    )

    list_filter = (
        'predicted_priority',
        'sentiment',
        'analyzed_at'
    )

    readonly_fields = ('analyzed_at',)
