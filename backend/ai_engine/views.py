from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.views import APIView

from accounts.permissions import IsSmartDeskUser
from smartdesk.api import success_response
from tickets.permissions import visible_tickets_for
from .serializers import AnalysisRequestSerializer, TicketAnalysisSerializer
from .services import analyze_ticket


class AnalyzeTicketView(APIView):
    permission_classes = [IsSmartDeskUser]

    def handle_exception(self, exc):
        # DRF parses JSON before dispatching post(); keep malformed input on
        # this endpoint aligned with the approved validation_error convention.
        if isinstance(exc, ParseError):
            exc = ValidationError({"non_field_errors": ["Malformed JSON request body."]})
        return super().handle_exception(exc)

    def post(self, request, ticket_id):
        request_serializer = AnalysisRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        # Apply object visibility before the analysis service can read or persist
        # analysis for this ticket. The route parameter is Ticket's database PK.
        ticket = get_object_or_404(visible_tickets_for(request.user), pk=ticket_id)
        analysis = analyze_ticket(ticket)
        return success_response(TicketAnalysisSerializer(analysis).data)


# Keep the existing URLconf import and endpoint name stable.
analyze_ticket_view = AnalyzeTicketView.as_view()
