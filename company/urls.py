from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    path('dashboard/', views.company_dashboard, name='dashboard'),
    path('alljobs/', views.alljobs_view, name='company_all_jobs'),
    path('postchoice/', views.post_choice_view, name='company_post_choice'),
    path('profile/', views.company_profile, name='profile'),
]
