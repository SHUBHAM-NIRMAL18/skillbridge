from django.urls import path
from . import views

app_name = 'candidate'

urlpatterns = [
    path('dashboard/', views.candidate_dashboard, name='dashboard'),
    # Add other URL patterns for the candidate app here as needed
]