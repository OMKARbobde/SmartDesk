from django.urls import path

from .views import (
    CsrfBootstrapView,
    CurrentUserProfileView,
    CurrentUserView,
    LoginView,
    LogoutView,
)


urlpatterns = [
    path("auth/csrf/", CsrfBootstrapView.as_view(), name="api-csrf"),
    path("auth/login/", LoginView.as_view(), name="api-login"),
    path("auth/logout/", LogoutView.as_view(), name="api-logout"),
    path("auth/me/", CurrentUserView.as_view(), name="api-current-user"),
    path("users/me/", CurrentUserProfileView.as_view(), name="api-current-user-profile"),
]
