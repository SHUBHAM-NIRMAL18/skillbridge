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
    Redirect users after login:
    1) If a safe 'next' was stored in session (from /login or google_start), honor it.
    2) Otherwise route by role (candidate/company).
    """
    def get_login_redirect_url(self, request):
        # Honor a safe “next” saved earlier (both password and Google flows can set it)
        next_url = request.session.pop("login_next", None)
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return next_url

        user = request.user
        if getattr(user, "role", None) == User.ROLE_CANDIDATE:
            return reverse("candidate:dashboard")
        elif getattr(user, "role", None) == User.ROLE_COMPANY:
            return reverse("company:dashboard")


class CandidateOnlySocialAdapter(DefaultSocialAccountAdapter):
    """
    Allows Google sign-in only for candidate accounts.
    - Candidates: can use password OR Google.
    - Companies: password only (block Google).
    """
    def pre_social_login(self, request, sociallogin):
        # Ensure the Google button was initiated from the candidate flow
        intended = request.session.get("intended_role")
        if intended != "candidate":
            messages.error(request, "Google sign-in is available for candidates only.")
            raise ImmediateHttpResponse(redirect(reverse("accounts:login")))

        # Require verified email from Google
        extra = sociallogin.account.extra_data or {}
        email_verified = extra.get("email_verified")
        email = (extra.get("email") or "").strip().lower()
        if email_verified is not True:
            messages.error(request, "Your Google email could not be verified.")
            raise ImmediateHttpResponse(redirect(reverse("accounts:login")))

        # Normalize the in-flight social user email
        if sociallogin.user:
            sociallogin.user.email = email

        # Link or block based on existing role/email
        try:
            existing = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            existing = None

        if existing:
            # If the email belongs to a company account, block Google login
            if existing.role == User.ROLE_COMPANY:
                messages.error(
                    request,
                    "This email belongs to a recruiter account. Please sign in with your password.",
                )
                raise ImmediateHttpResponse(redirect(reverse("accounts:login")))

            # Existing candidate → attach the social account and LOG IN immediately.
            # Short-circuit the pipeline so the session is definitely established.
            sociallogin.connect(request, existing)

            # Respect any safe `login_next` captured earlier; perform_login will then
            # delegate to the AccountAdapter.get_login_redirect_url (above).
            raise ImmediateHttpResponse(perform_login(request, existing))

        # New user via Google → allow allauth to continue to create the user.
        # populate_user() below forces candidate role.

    def populate_user(self, request, sociallogin, data):
        """
        New user via Google → force candidate role and normalized email.
        (Called only when the account doesn't already exist.)
        """
        user = super().populate_user(request, sociallogin, data)
        user.email = (user.email or "").strip().lower()
        user.role = User.ROLE_CANDIDATE
        return user
