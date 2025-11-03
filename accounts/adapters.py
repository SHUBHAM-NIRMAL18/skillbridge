# accounts/adapters.py
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import perform_login
from allauth.core.exceptions import ImmediateHttpResponse

from .models import User


class RoleRedirectAccountAdapter(DefaultAccountAdapter):
    """
    After *any* successful login, send users:
      - to a safe `next=` if present
      - otherwise to the right dashboard by role
      - fallback (never /login/): candidate dashboard
    """
    def get_login_redirect_url(self, request):
        next_url = request.session.pop("login_next", None)
        if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
            return next_url

        user = request.user
        if getattr(user, "role", None) == User.ROLE_CANDIDATE:
            return reverse("candidate:dashboard")
        if getattr(user, "role", None) == User.ROLE_COMPANY:
            return reverse("company:dashboard")

        # Important: never fall back to the login page
        return reverse("candidate:dashboard")


class CandidateOnlySocialAdapter(DefaultSocialAccountAdapter):
    """
    Google sign-in is allowed only for candidate accounts.
    - Existing company account -> block
    - Existing user with no role -> set candidate role
    - New user -> role set to candidate in populate_user()
    """

    def pre_social_login(self, request, sociallogin):
        # Ensure the flow was started from the candidate Google button
        intended = request.session.get("intended_role")
        if intended != "candidate":
            messages.error(request, "Google sign-in is available for candidates only.")
            raise ImmediateHttpResponse(redirect(reverse("accounts:login")))

        # Require verified Google email (handle True/"true"/1)
        extra = sociallogin.account.extra_data or {}
        email = (extra.get("email") or "").strip().lower()
        ev_raw = extra.get("email_verified")
        email_verified = ev_raw in (True, "true", "True", 1, "1")
        if not email_verified:
            messages.error(request, "Your Google email could not be verified.")
            raise ImmediateHttpResponse(redirect(reverse("accounts:login")))

        # Normalize the in-flight user email (for new user path)
        if sociallogin.user:
            sociallogin.user.email = email

        # Existing local user?
        try:
            existing = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            existing = None

        if existing:
            # Company accounts cannot use Google
            if existing.role == User.ROLE_COMPANY:
                messages.error(
                    request,
                    "This email belongs to a recruiter account. Please sign in with your password.",
                )
                raise ImmediateHttpResponse(redirect(reverse("accounts:login")))

            # Ensure legacy users always have a role
            if not existing.role:
                existing.role = User.ROLE_CANDIDATE
                existing.save(update_fields=["role"])

            # Link this Google account if not already linked
            if not sociallogin.is_existing:
                sociallogin.connect(request, existing)

            # Establish the session and short-circuit the pipeline
            raise ImmediateHttpResponse(perform_login(request, existing))

        # New user -> continue pipeline; populate_user sets candidate role

    def populate_user(self, request, sociallogin, data):
        # Called only for new users created via Google
        user = super().populate_user(request, sociallogin, data)
        user.email = (user.email or "").strip().lower()
        user.role = User.ROLE_CANDIDATE
        return user
