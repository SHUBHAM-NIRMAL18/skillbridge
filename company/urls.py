from django.urls import path
from . import views
from .views import InternshipWizard
from django.views.generic import TemplateView 

app_name = 'company'

urlpatterns = [
    path('dashboard/', views.company_dashboard, name='dashboard'),
    path('alljobs/', views.alljobs_view, name='company_all_jobs'),
    path('postchoice/', views.post_choice_view, name='company_post_choice'),
    path('profile/', views.company_profile, name='profile'),
     path(
      'internship/create/',
      InternshipWizard.as_view(url_name='company:internship_step', done_step_name='review'),
      name='internship_create'
    ),
    path(
      'internship/create/<str:step>/',
      InternshipWizard.as_view(),
      name='internship_step'
    ),
    # success page…
    path('internship/success/', TemplateView.as_view(
         template_name='company/internship_success.html'),
         name='internship_success'),
]
