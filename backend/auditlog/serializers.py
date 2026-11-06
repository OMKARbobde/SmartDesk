from rest_framework import serializers

from .models import AuditEvent


class AuditEventReadSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()
    ticket = serializers.SerializerMethodField()
    assignment = serializers.SerializerMethodField()
    target_user = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = (
            "id", "event_type", "created_at", "actor", "ticket", "assignment",
            "target_user", "details",
        )

    @staticmethod
    def get_actor(obj):
        user = obj.actor
        display_name = None
        if user is not None:
            display_name = user.get_full_name().strip() or user.username
        return {"id": obj.actor_user_id_snapshot, "display_name": display_name}

    @staticmethod
    def get_ticket(obj):
        if obj.ticket_pk_snapshot is None and obj.ticket_public_id_snapshot is None:
            return None
        return {"id": obj.ticket_pk_snapshot, "ticket_id": obj.ticket_public_id_snapshot}

    @staticmethod
    def get_assignment(obj):
        if obj.assignment_pk_snapshot is None:
            return None
        return {"id": obj.assignment_pk_snapshot}

    @staticmethod
    def get_target_user(obj):
        if obj.target_user_id_snapshot is None:
            return None
        user = obj.target_user
        display_name = None
        if user is not None:
            display_name = user.get_full_name().strip() or user.username
        return {"id": obj.target_user_id_snapshot, "display_name": display_name}
