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
    def get_login_redirect_url(self, request):
        next_url = request.session.pop("login_next", None)
        if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
            return next_url

        user = request.user
        if getattr(user, "role", None) == User.ROLE_CANDIDATE:
            return reverse("candidate:dashboard")
        if getattr(user, "role", None) == User.ROLE_COMPANY:
            return reverse("company:dashboard")

        
        return reverse("candidate:dashboard")



class CandidateOnlySocialAdapter(DefaultSocialAccountAdapter):
    """
    Allow Google only for candidates.
    If the email matches an existing candidate: attach the social account (if not already)
    and log them in immediately.
    """

    def pre_social_login(self, request, sociallogin):
        # Only allow when the flow was started from candidate Google button
        intended = request.session.get("intended_role")
        if intended != "candidate":
            messages.error(request, "Google sign-in is available for candidates only.")
            raise ImmediateHttpResponse(redirect(reverse("accounts:login")))

        # Require verified Google email
        extra = sociallogin.account.extra_data or {}
        email_verified = extra.get("email_verified")
        email = (extra.get("email") or "").strip().lower()
        if email_verified is not True:
            messages.error(request, "Your Google email could not be verified.")
            raise ImmediateHttpResponse(redirect(reverse("accounts:login")))

        # Normalize the in-flight user
        if sociallogin.user:
            sociallogin.user.email = email

        # Try to find an existing local account
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

            # Attach the social account to the existing user if not already linked.
            # (sociallogin.is_existing is True if this social account is already linked.)
            if not sociallogin.is_existing:
                # This is safe even if request.user is anonymous.
                sociallogin.connect(request, existing)

        
            raise ImmediateHttpResponse(perform_login(request, existing))

        # No existing user: continue the normal pipeline; populate_user sets candidate role.

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        user.email = (user.email or "").strip().lower()
        user.role = User.ROLE_CANDIDATE
        return user
