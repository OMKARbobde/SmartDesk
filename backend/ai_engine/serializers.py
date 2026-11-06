from collections.abc import Mapping

from rest_framework import serializers

from .models import TicketAnalysis


class AnalysisRequestSerializer(serializers.Serializer):
    """The analysis action accepts an empty object (or an omitted body)."""

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError({"non_field_errors": ["Expected an empty JSON object."]})
        if data:
            raise serializers.ValidationError({
                str(key): ["This action does not accept input fields."] for key in sorted(data)
            })
        return {}


class TicketAnalysisSerializer(serializers.ModelSerializer):
    message = serializers.SerializerMethodField()
    ticket_id = serializers.CharField(source="ticket.ticket_id", read_only=True)
    predicted_priority = serializers.SerializerMethodField()
    sentiment = serializers.SerializerMethodField()
    analyzed_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = TicketAnalysis
        fields = (
            "message",
            "ticket_id",
            "predicted_category",
            "predicted_priority",
            "sentiment",
            "confidence_score",
            "suggested_response",
            "analyzed_at",
        )

    @staticmethod
    def get_message(_obj):
        return "Ticket analyzed successfully"

    @staticmethod
    def _canonical_enum(value):
        if value is None:
            return None
        return str(value).strip().upper()

    def get_predicted_priority(self, obj):
        return self._canonical_enum(obj.predicted_priority)

    def get_sentiment(self, obj):
        return self._canonical_enum(obj.sentiment)
