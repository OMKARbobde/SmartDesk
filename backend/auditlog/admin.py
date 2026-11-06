from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "event_type", "actor_user_id_snapshot", "ticket_public_id_snapshot")
    list_filter = ("event_type", "created_at")
    search_fields = ("ticket_public_id_snapshot", "actor_user_id_snapshot")
    readonly_fields = tuple(field.name for field in AuditEvent._meta.fields)
    ordering = ("-created_at", "id")

    def has_module_permission(self, request):
        return bool(request.user.is_active and request.user.is_staff and request.user.role == "ADMIN")

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
