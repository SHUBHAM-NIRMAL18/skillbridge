from django import forms
from django.core.exceptions import ValidationError
from datetime import date
import re

from .models import (
    Profile, Education, SocialLink,
    PROVINCE_CHOICES, GENDER_CHOICES, EXPERIENCE_LEVEL_CHOICES
)

PHONE_RE = re.compile(r"^\+?\d[\d\-\s]{6,}$")


class CandidateOnboardingForm(forms.ModelForm):
    # Step 1: Personal info
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. John',
            'id': 'id_first_name'
        })
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Doe',
            'id': 'id_last_name'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. +977 9800000000',
            'id': 'id_phone_number'
        })
    )
    gender = forms.ChoiceField(
        choices=[('', 'Select Gender')] + GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'id_gender'})
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-lg', 'id': 'id_date_of_birth'})
    )
    province = forms.ChoiceField(
        choices=[('', 'Select Province')] + PROVINCE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'id_province'})
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Kathmandu',
            'id': 'id_city'
        })
    )
    current_address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Baneshwor, Kathmandu',
            'id': 'id_current_address'
        })
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'id': 'id_profile_picture'})
    )

    # Step 2: Professional Persona & Skills
    designation = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Full Stack Developer, Data Scientist, UI/UX Designer',
            'id': 'id_designation'
        })
    )
    experience_level = forms.ChoiceField(
        choices=[('', 'Select Experience Level')] + EXPERIENCE_LEVEL_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'id_experience_level'})
    )
    sectors = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Technology, FinTech, Design',
            'id': 'id_sectors'
        })
    )
    skills = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Python, Django, React, PostgreSQL',
            'id': 'id_skills'
        })
    )
    about_me = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Brief summary of your professional background, passions, and career aspirations...',
            'id': 'id_about_me'
        })
    )

    # Step 3: Education & Resume & Links
    institution = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Tribhuvan University / Kathmandu University',
            'id': 'id_institution'
        })
    )
    degree = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Bachelor in Computer Science / IT / BBA',
            'id': 'id_degree'
        })
    )
    field_of_study = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Software Engineering',
            'id': 'id_field_of_study'
        })
    )
    edu_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_edu_start_date'})
    )
    edu_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_edu_end_date'})
    )
    resume = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx', 'id': 'id_resume'})
    )
    linkedin_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://linkedin.com/in/yourprofile',
            'id': 'id_linkedin_url'
        })
    )
    github_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://github.com/yourusername',
            'id': 'id_github_url'
        })
    )
    portfolio_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://yourportfolio.com',
            'id': 'id_portfolio_url'
        })
    )

    class Meta:
        model = Profile
        fields = [
            'first_name', 'last_name', 'phone_number', 'gender', 'date_of_birth',
            'province', 'city', 'current_address', 'profile_picture',
            'designation', 'experience_level', 'sectors', 'skills', 'about_me',
            'resume',
        ]

    def clean_first_name(self):
        val = (self.cleaned_data.get('first_name') or '').strip()
        if any(ch.isdigit() for ch in val):
            raise ValidationError("First name cannot contain numbers.")
        return val

    def clean_last_name(self):
        val = (self.cleaned_data.get('last_name') or '').strip()
        if any(ch.isdigit() for ch in val):
            raise ValidationError("Last name cannot contain numbers.")
        return val

    def clean_phone_number(self):
        phone = (self.cleaned_data.get('phone_number') or '').strip()
        if phone and not PHONE_RE.match(phone):
            raise ValidationError("Please enter a valid phone number (at least 7 digits).")
        return phone

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            if dob > date.today():
                raise ValidationError("Date of birth cannot be in the future.")
            if (date.today().year - dob.year) < 16:
                raise ValidationError("You must be at least 16 years old.")
        return dob

    def clean_sectors(self):
        val = self.cleaned_data.get('sectors') or ''
        parts = [p.strip().strip('"').strip("'") for p in val.replace(';', ',').split(',') if p.strip()]
        if not parts:
            raise ValidationError("Please select or enter at least one sector.")
        return ", ".join(parts)

    def clean_skills(self):
        val = self.cleaned_data.get('skills') or ''
        parts = [p.strip().strip('"').strip("'") for p in val.replace(';', ',').split(',') if p.strip()]
        if not parts:
            raise ValidationError("Please select or enter at least one skill.")
        return ", ".join(parts)
