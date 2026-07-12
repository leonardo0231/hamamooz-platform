from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from apps.accounts.api.views import ChangePasswordView, LoginView, LogoutView, MeView

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("verify/", TokenVerifyView.as_view(), name="auth-verify"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
]
