# candidate/urls.py
from django.urls import path
from django.shortcuts import redirect
from .views import candidate_dashboard, ProfileWizardView, ProfileCompleteView

app_name = "candidate"

urlpatterns = [
    path('dashboard/', candidate_dashboard, name='dashboard'),
    path('profile/', lambda r: redirect('candidate:profile', step='personal'), name='profile_index'),

    # 👇 specific FIRST
    path('profile/complete/', ProfileCompleteView.as_view(), name='profile_complete'),

    # 👇 dynamic AFTER
    path('profile/<str:step>/', ProfileWizardView.as_view(), name='profile'),
]
