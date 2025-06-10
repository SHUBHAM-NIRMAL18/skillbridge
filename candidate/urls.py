from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.candidate_dashboard, name='candidate_dashboard'),
    # Add other URL patterns for the candidate app here as needed
]