from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages

from .forms import CompanyRegistrationForm, CandidateRegistrationForm, EmailAuthenticationForm

def register_company(request):
    if request.method == "POST":
        form = CompanyRegistrationForm(request.POST)
        if form.is_valid():
            # 1) create user
            user = form.save()
            # 2) authenticate so user.backend is set
            user = authenticate(
                request,
                username=user.username,        # this holds the email
                password=form.cleaned_data["password1"]
            )
            if user is not None:
                # 3) now login will work
                login(request, user)
                return redirect("accounts:login")
        # fall through to re-render form with errors
    else:
        form = CompanyRegistrationForm()
    return render(request, "accounts/company_register.html", {"form": form})


def register_candidate(request):
    if request.method == "POST":
        form = CandidateRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user = authenticate(
                request,
                username=user.username,
                password=form.cleaned_data["password1"]
            )
            if user is not None:
                login(request, user)
                return redirect("accounts:login")
    else:
        form = CandidateRegistrationForm()
    return render(request, "accounts/candidate_register.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm  # if you’ve wired this up

    def get_success_url(self):
        user = self.request.user
        if user.role == user.ROLE_COMPANY:
            return reverse("company:dashboard")
        elif user.role == user.ROLE_CANDIDATE:
            return reverse("candidate:dashboard")
        return super().get_success_url()
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "You are successfully logged in.")
        return response


class CustomLogoutView(LogoutView):
    next_page = "index"
