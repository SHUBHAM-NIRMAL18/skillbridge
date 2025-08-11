from django.urls import path
from django.shortcuts import redirect
from .views import candidate_dashboard, ProfileWizardView, ProfileCompleteView, ProfilePreviewView

app_name = "candidate"

urlpatterns = [
    path('dashboard/', candidate_dashboard, name='dashboard'),

    # Wizard entry
    path('profile/', lambda r: redirect('candidate:profile', step='personal'), name='profile_index'),

    # Preview page (read-only summary with edit links)
    path('profile/preview/', ProfilePreviewView.as_view(), name='profile_preview'),

    # Complete page
    path('profile/complete/', ProfileCompleteView.as_view(), name='profile_complete'),

    # Dynamic wizard step
    path('profile/<str:step>/', ProfileWizardView.as_view(), name='profile'),
]
# candidate/urls.py
from applications.views import my_applications
urlpatterns += [ path("applications/", my_applications, name="applications") ]
