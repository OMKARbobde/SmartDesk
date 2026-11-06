from django.contrib import admin
from .models import Assignment


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):

    list_display = (
        'ticket',
        'assigned_to',
        'assigned_by',
        'status',
        'assigned_at'
    )

    list_filter = ('status', 'assigned_at')
    search_fields = ('ticket__ticket_id', 'assigned_to__employee_id')