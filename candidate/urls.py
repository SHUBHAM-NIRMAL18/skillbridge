from django.urls import path
from django.shortcuts import redirect
from .views import (
    candidate_dashboard,
    ProfileWizardView,
    ProfileCompleteView,
)
# HTMX: lazy-import the add-row view via string to avoid circulars if you prefer,
# but we'll import directly once it's in views.py in the next step.

from .views import ProfileFormsetAddRowView  # <-- NEW

app_name = "candidate"

urlpatterns = [
    path('dashboard/', candidate_dashboard, name='dashboard'),
    path('profile/', lambda r: redirect('candidate:profile', step='personal'), name='profile_index'),

    # specific FIRST
    path('profile/complete/', ProfileCompleteView.as_view(), name='profile_complete'),

    # HTMX endpoint to add a new inline formset row for a given step
    path('profile/<str:step>/add-row/', ProfileFormsetAddRowView.as_view(), name='profile_add_row'),  # <-- NEW

    # dynamic AFTER
    path('profile/<str:step>/', ProfileWizardView.as_view(), name='profile'),
]
