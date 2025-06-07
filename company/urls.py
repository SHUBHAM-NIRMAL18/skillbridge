from django.urls import path
from . import views

urlpatterns = [
    path('base/', views.base_view, name='company_base'),
]
