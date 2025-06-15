from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(AbstractUser):
    ROLE_COMPANY   = "company"
    ROLE_CANDIDATE = "candidate"
    ROLE_CHOICES = [
        (ROLE_COMPANY,   "Company"),
        (ROLE_CANDIDATE, "Candidate"),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        help_text="Determines which dashboard you see after login."
    )
