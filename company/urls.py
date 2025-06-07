from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='company_dashboard'),
    path('alljobs/', views.alljobs_view, name='company_all_jobs'),
]
