from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(AbstractUser):
    email = models.EmailField(unique=True)   # ← enforce unique emails
    ROLE_COMPANY   = "company"
    ROLE_CANDIDATE = "candidate"
    ROLE_CHOICES = [
        (ROLE_COMPANY,   "Company"),
        (ROLE_CANDIDATE, "Candidate"),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_onboarded = models.BooleanField(default=False)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    @property
    def has_completed_onboarding(self):
        if self.is_onboarded:
            return True
        # Backward compatibility for existing users who already completed profiles
        if self.role == self.ROLE_COMPANY:
            return hasattr(self, "company_profile") and bool(getattr(self.company_profile, "first_name", None))
        elif self.role == self.ROLE_CANDIDATE:
            profile = getattr(self, "profile", None)
            return profile is not None and bool(profile.first_name) and bool(profile.designation)
        return False