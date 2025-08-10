from django.urls import path
from website import views

app = 'website'

urlpatterns = [
    path('index/', views.home_view, name='index'),
    #path('login/', views.login_view, name='login'),
    path('privacy/', views.privacy_policy_view, name='privacy'),
    path('terms/', views.termcondition_view, name='terms'),
    path("internships/", views.internships_list_view, name="internship"),
    path("internships/<int:pk>/", views.internship_detail_view, name="internship_detail"),
    path("companies/<int:pk>/", views.company_detail_view, name="company_detail"),
    # Add other URL patterns for the website app here as needed
]

