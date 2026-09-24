from django.urls import path
from . import views

app_name = "applications"

urlpatterns = [
    path("apply/preview/", views.apply_preview, name="apply_preview"),
    path("apply/submit/",  views.apply_submit,  name="apply_submit"),

    path("my/",            views.my_applications,     name="my_applications"),
    path("<int:pk>/withdraw/", views.withdraw_application, name="withdraw"),
    path("<int:pk>/delete/", views.delete_application, name="delete"),
    path("<int:pk>/detail/", views.application_detail, name="detail"),

    # Offer Letter workflow
    path("<int:app_id>/offer/create/", views.create_offer_letter, name="create_offer"),
    path("<int:app_id>/offer/", views.view_offer_letter, name="view_offer"),
    path("<int:app_id>/offer/respond/", views.respond_offer_letter, name="respond_offer"),

    # Secure resume download
    path("<int:pk>/resume/download/", views.download_application_resume, name="download_resume"),

    # Interview Scheduling workflow
    path("<int:app_id>/interview/schedule/", views.schedule_interview, name="schedule_interview"),
    path("interview/<int:pk>/rsvp/", views.interview_rsvp, name="interview_rsvp"),
    path("interview/<int:pk>/ics/", views.interview_ics_download, name="interview_ics"),
    path("interview/<int:pk>/cancel/", views.interview_cancel, name="interview_cancel"),
    path("interview/<int:pk>/complete/", views.interview_complete, name="interview_complete"),
]


