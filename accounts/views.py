from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView

from .forms import CompanyRegistrationForm, CandidateRegistrationForm

def register_company(request):
    if request.method == "POST":
        form = CompanyRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("company:dashboard")
    else:
        form = CompanyRegistrationForm()
    return render(request, "accounts/company_register.html", {"form": form})

def register_candidate(request):
    if request.method == "POST":
        form = CandidateRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("candidate:dashboard")
    else:
        form = CandidateRegistrationForm()
    return render(request, "accounts/candidate_register.html", {"form": form})

class CustomLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_success_url(self):
        user = self.request.user
        if user.role == user.ROLE_COMPANY:
            return reverse("company:dashboard")
        elif user.role == user.ROLE_CANDIDATE:
            return reverse("candidate:dashboard")
        return super().get_success_url()

class CustomLogoutView(LogoutView):
    next_page = "index"

