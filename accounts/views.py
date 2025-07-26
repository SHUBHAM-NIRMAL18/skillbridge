# accounts/views.py
from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView

from .forms import (
    CompanyRegistrationForm,
    CandidateRegistrationForm,
    EmailAuthenticationForm,
)

def register_company(request):
    if request.method == "POST":
        form = CompanyRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Company registered successfully.")
            return redirect("accounts:login")
    else:
        form = CompanyRegistrationForm()
    return render(request, "accounts/company_register.html", {"form": form})


def register_candidate(request):
    if request.method == "POST":
        form = CandidateRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Candidate registered successfully.")
            return redirect("accounts:login")
    else:
        form = CandidateRegistrationForm()
    return render(request, "accounts/candidate_register.html", {"form": form})


class CustomLoginView(LoginView):
    template_name       = "accounts/login.html"
    authentication_form = EmailAuthenticationForm

    def form_valid(self, form):
        # first let Django log in the user
        response = super().form_valid(form)

        # then honor the “keep me signed in” checkbox
        remember = form.cleaned_data.get("remember_me", False)
        if remember:
            # keep the session alive for the full cookie age
            self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        else:
            # expire on browser close
            self.request.session.set_expiry(0)

        messages.success(self.request, "You are successfully logged in.")
        return response

    def get_success_url(self):
        user = self.request.user
        if user.role == user.ROLE_COMPANY:
            return reverse("company:dashboard")
        return reverse("candidate:dashboard")


class CustomLogoutView(LogoutView):
    next_page = "index"

    def dispatch(self, request, *args, **kwargs):
        messages.success(request, "You have successfully logged out.")
        return super().dispatch(request, *args, **kwargs)
