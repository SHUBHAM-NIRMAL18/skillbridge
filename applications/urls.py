from django.urls import path
from . import views

app_name = "applications"

urlpatterns = [
    path("apply/preview/", views.apply_preview, name="apply_preview"),
    path("apply/submit/",  views.apply_submit,  name="apply_submit"),

    path("my/",            views.my_applications,     name="my_applications"),
    path("<int:pk>/withdraw/", views.withdraw_application, name="withdraw"),
]
