from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class CompanyRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        # assign the email field
        user.email = self.cleaned_data["email"]
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
        # assign the email field
        user.email = self.cleaned_data["email"]
        user.role = User.ROLE_CANDIDATE
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    # Django’s AuthenticationForm already accepts `request` in __init__
    username = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={"autofocus": True})
    )
    remember_me = forms.BooleanField(
        label="Keep me signed in",
        required=False,
        initial=False
    )
