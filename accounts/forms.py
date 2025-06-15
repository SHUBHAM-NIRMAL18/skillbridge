from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CompanyRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.ROLE_COMPANY
        if commit:
            user.save()
        return user

class CandidateRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.ROLE_CANDIDATE
        if commit:
            user.save()
        return user