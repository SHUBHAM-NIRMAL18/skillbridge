# candidate/urls.py
from django.urls import path
from django.shortcuts import redirect
from .views import (
    candidate_dashboard, ProfileWizardView, ProfileCompleteView,
    ProfilePreviewView, recommended_demo, inbox, support, feedback
)
from applications.views import my_applications

app_name = "candidate"

urlpatterns = [
    path('dashboard/', candidate_dashboard, name='dashboard'),
    path('inbox/', inbox, name='inbox'),
    path('support/', support, name='support'),
    path('feedback/', feedback, name='feedback'),

    # Wizard
    path('profile/', lambda r: redirect('candidate:profile', step='personal'), name='profile_index'),
    path('profile/preview/', ProfilePreviewView.as_view(), name='profile_preview'),
    path('profile/complete/', ProfileCompleteView.as_view(), name='profile_complete'),
    path('profile/<str:step>/', ProfileWizardView.as_view(), name='profile'),

    # Applications
    path('applications/', my_applications, name='applications'),

    path('recommended-demo/', recommended_demo, name='recommended_demo'),
]
