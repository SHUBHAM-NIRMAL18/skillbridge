from django.urls import path
from .views import (
    register_company,
    register_candidate,
    CustomLoginView,
    CustomLogoutView,
    
)

app_name = "accounts"

urlpatterns = [
    path("register/company/",    register_company,   name="register_company"),
    path("register/candidate/",  register_candidate, name="register_candidate"),
    path("login/",  CustomLoginView.as_view(),  name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),

]
