from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from smartdesk.api import success_response
from .authentication import SmartDeskSessionAuthentication

from .serializers import CurrentUserSerializer, LoginSerializer, ProfileUpdateSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfBootstrapView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request):
        return success_response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    """Explicit CSRF protection is required because login is anonymous."""

    # Anonymous requests still yield no authenticated user; the authenticator's
    # challenge header ensures AuthenticationFailed is emitted as HTTP 401.
    authentication_classes = (SmartDeskSessionAuthentication,)
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        django_login(request, user)

        # django_login rotates the CSRF secret. Return the new masked token and
        # let the CSRF response middleware update the cookie for subsequent writes.
        token = get_token(request)
        return success_response(
            {"user": CurrentUserSerializer(user).data},
            meta={"csrf_token": token},
        )


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        django_logout(request)
        return Response(status=204)


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return success_response({"user": CurrentUserSerializer(request.user).data})


@method_decorator(csrf_protect, name="dispatch")
class CurrentUserProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return success_response({"user": CurrentUserSerializer(user).data})
