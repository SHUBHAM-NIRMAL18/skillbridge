from django.urls import path
from .views import (
    register_company,
    register_candidate,
    CustomLoginView,
    CustomLogoutView,
    google_login_start,
    check_email_exists,
)

app_name = "accounts"

urlpatterns = [
    path("register/company/",    register_company,   name="register_company"),
    path("register/candidate/",  register_candidate, name="register_candidate"),
    path("login/",  CustomLoginView.as_view(),  name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),

    path("accounts/google/start/", google_login_start, name="google_start"),
    path("check-email/", check_email_exists, name="check_email_exists"),
]
