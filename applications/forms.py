from django import forms
from .models import OfferLetter

class OfferLetterForm(forms.ModelForm):
    class Meta:
        model = OfferLetter
        fields = [
            'job_title',
            'offered_salary',
            'joining_date',
            'work_location',
            'employment_type',
            'expiration_date',
            'hr_name',
            'hr_designation',
            'hr_signature',
            'terms_and_conditions',
        ]
        widgets = {
            'job_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Senior Django Developer'}),
            'offered_salary': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. NPR 50,000 / month'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'work_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Kathmandu (On-site)'}),
            'employment_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Full-Time / 6-Month Internship'}),
            'expiration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hr_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name of Recruiter/HR'}),
            'hr_designation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. HR Manager / Co-founder'}),
            'hr_signature': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter probation duration, working hours, benefits, confidentiality terms, etc.'}),
        }
