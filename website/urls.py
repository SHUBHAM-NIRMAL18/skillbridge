from django.urls import path
from . import views

urlpatterns = [
    path('index/', views.home_view, name='index'),
    path('login/', views.login_view, name='login'),
    # Add other URL patterns for the website app here as needed
]

