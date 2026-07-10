# accounts/views.py
from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout

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
    def get(self, request):
        logout(request)
        messages.success(request, "You have successfully logged out.")
        return redirect("accounts:login")
    

from django.middleware.csrf import get_token
from django.http import HttpResponse
from django.utils.http import url_has_allowed_host_and_scheme

def google_login_start(request):
    request.session["intended_role"] = "candidate"

    next_url = request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        request.session["login_next"] = next_url

    csrf_token = get_token(request)
    html = f"""
    <html><body>
      <form id="go" action="/accounts/google/login/" method="post">
        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
        <input type="hidden" name="process" value="login">
      </form>
      <script>document.getElementById('go').submit();</script>
    </body></html>
    """
    return HttpResponse(html)


from django.http import JsonResponse
from .models import User

def check_email_exists(request):
    email = request.GET.get("email", "").strip().lower()
    exists = False
    if email:
        exists = User.objects.filter(email=email).exists()
    return JsonResponse({"exists": exists})

