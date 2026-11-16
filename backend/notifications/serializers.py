from rest_framework import serializers

from .models import Notification


class NotificationReadSerializer(serializers.ModelSerializer):
    related_ticket = serializers.SerializerMethodField()
    related_assignment = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id", "notification_type", "title", "message", "related_ticket",
            "related_assignment", "is_read", "created_at",
        )

    @staticmethod
    def get_related_ticket(obj):
        if obj.related_ticket_id is None:
            return None
        return {"id": obj.related_ticket_id, "ticket_id": obj.related_ticket.ticket_id}

    @staticmethod
    def get_related_assignment(obj):
        if obj.related_assignment_id is None:
            return None
        return {"id": obj.related_assignment_id}
