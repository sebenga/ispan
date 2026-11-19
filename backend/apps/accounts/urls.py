from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomerProfileView,
    EnableWorkerProfileView,
    LoginView,
    LogoutView,
    MeView,
    OtpRequestView,
    OtpVerifyView,
    RegisterView,
    SavedAddressView,
    WorkerProfileView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh-legacy"),
    path("otp/request/", OtpRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OtpVerifyView.as_view(), name="otp-verify"),
    path("me/", MeView.as_view(), name="me"),
    path("me/enable-worker/", EnableWorkerProfileView.as_view(), name="enable-worker"),
    path("worker/profile/", WorkerProfileView.as_view(), name="worker-profile"),
    path("customers/me/", CustomerProfileView.as_view(), name="customer-me"),
    path("customers/me/addresses/", SavedAddressView.as_view(), name="customer-addresses"),
]
