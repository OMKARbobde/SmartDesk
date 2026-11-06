from django.contrib import admin
from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):

    list_display = (
        'ticket_id',
        'title',
        'created_by',
        'department',
        'priority',
        'status',
        'created_at'
    )

    search_fields = ('ticket_id', 'title')
    list_filter = ('status', 'priority', 'department')