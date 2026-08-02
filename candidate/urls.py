# candidate/urls.py
from django.urls import path
from django.shortcuts import redirect
from .views import (
    candidate_dashboard, ProfileWizardView, ProfileCompleteView,
    ProfilePreviewView, recommended_demo, log_candidate_event, inbox, support, feedback,
    candidate_registered_events, candidate_bookmarks_list, toggle_bookmark
)
from applications.views import my_applications

app_name = "candidate"

urlpatterns = [
    path('dashboard/', candidate_dashboard, name='dashboard'),
    path('inbox/', inbox, name='inbox'),
    path('support/', support, name='support'),
    path('feedback/', feedback, name='feedback'),

    # Bookmarks
    path('bookmarks/', candidate_bookmarks_list, name='bookmarks'),
    path('bookmarks/toggle/', toggle_bookmark, name='toggle_bookmark'),

    # Wizard
    path('profile/', lambda r: redirect('candidate:profile', step='personal'), name='profile_index'),
    path('profile/preview/', ProfilePreviewView.as_view(), name='profile_preview'),
    path('profile/complete/', ProfileCompleteView.as_view(), name='profile_complete'),
    path('profile/<str:step>/', ProfileWizardView.as_view(), name='profile'),

    # Applications
    path('applications/', my_applications, name='applications'),

    # Recommendations
    path('recommendations/', recommended_demo, name='recommendations'),
    path('recommended-demo/', lambda r: redirect('candidate:recommendations', permanent=True), name='recommended_demo'),
    path('log-event/', log_candidate_event, name='log_event'),

    path('events/', candidate_registered_events, name='registered_events'),
]
