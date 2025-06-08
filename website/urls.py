from django.urls import path
from . import views

urlpatterns = [
    path('index/', views.home_view, name='index'),
    # Add other URL patterns for the website app here as needed
]

