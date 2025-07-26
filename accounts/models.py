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
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]