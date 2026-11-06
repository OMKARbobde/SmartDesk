from rest_framework.authentication import SessionAuthentication


class SmartDeskSessionAuthentication(SessionAuthentication):
    """Use Django sessions while making unauthenticated API errors HTTP 401."""

    def authenticate_header(self, request):
        return "Session"
