from django.urls import path
from website import views

app = 'website'

urlpatterns = [
    path('', views.home_view, name='index'),
    #path('login/', views.login_view, name='login'),
    path('privacy/', views.privacy_policy_view, name='privacy'),
    path('terms/', views.termcondition_view, name='terms'),
    path("internships/", views.internships_list_view, name="internship"),
    path("internships/<int:pk>/", views.internship_detail_view, name="internship_detail"),
    path("jobs/", views.jobs_list_view, name="jobs_list"),
    path("jobs/<int:pk>/", views.job_detail_view, name="job_detail"),
    path("companies/<int:pk>/", views.company_detail_view, name="company_detail"),
    path("events/", views.events_list_view, name="events_list"),
    path("events/<int:pk>/", views.event_detail_view, name="event_detail"),
    path("events/<int:pk>/register/", views.event_register_toggle, name="event_register_toggle"),
    # Add other URL patterns for the website app here as needed
]

