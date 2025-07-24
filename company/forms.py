from django import forms
from .models import CompanyProfile, InternshipPost
from django.utils import timezone
from datetime import timedelta
import re
from ckeditor.widgets import CKEditorWidget
from taggit.forms import TagWidget

class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = [
            'first_name', 'last_name', 'industry', 'founded_date',
            'company_size', 'about_company', 'phone', 'website_url',
            'province', 'city', 'postal_code', 'current_address',
            'social_link','logo',
        ]
        widgets = {
            'first_name':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'industry':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Industry'}),
            'founded_date':    forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'company_size':    forms.Select(attrs={'class': 'form-select'}),
            'about_company':   forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us about your company…'
            }),
            'logo':            forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'phone':           forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'website_url':     forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
            'province':        forms.Select(attrs={'class': 'form-select'}),
            'city':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'postal_code':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
            'current_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current Address'}),
            'social_link':     forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        return phone
    

class BasicDetailsForm(forms.ModelForm):
    class Meta:
        model = InternshipPost
        fields = [
            'title', 'city', 'location', 'sector',
            'application_deadline', 'type', 'level',
            'openings', 'comp_min', 'comp_max', 'comp_frequency',
        ]
        widgets = {
            # same widgets as before for two‑column layout…
            'title':               forms.TextInput(attrs={'class':'form-control', 'placeholder':'Internship Title'}),
            'city':                forms.TextInput(attrs={'class':'form-control', 'placeholder':'City'}),
            'location':            forms.Select(attrs={'class':'form-select'}),
            'sector':              forms.Select(attrs={'class':'form-select'}),
            'application_deadline':forms.DateInput(attrs={'type':'date','class':'form-control'}),
            'type':                forms.Select(attrs={'class':'form-select'}),
            'level':               forms.Select(attrs={'class':'form-select'}),
            'openings':            forms.NumberInput(attrs={'class':'form-control','min':1}),
            'comp_min':            forms.NumberInput(attrs={'class':'form-control','placeholder':'Min Salary'}),
            'comp_max':            forms.NumberInput(attrs={'class':'form-control','placeholder':'Max Salary'}),
            'comp_frequency':      forms.Select(attrs={'class':'form-select'}),
        }

    def clean(self):
        cleaned = super().clean()

        # — Strip and validate title —
        title = cleaned.get('title', '')
        if title:
            title = title.strip()
            cleaned['title'] = title
            if len(title) < 5:
                self.add_error('title', "Title must be at least 5 characters long.")

        # — Strip and validate city (letters, spaces, hyphens only) —
        city = cleaned.get('city', '')
        if city:
            city = city.strip()
            cleaned['city'] = city
            if not re.match(r'^[A-Za-z\s\-]+$', city):
                self.add_error('city', "City may only contain letters, spaces, or hyphens.")

        # — Salary bounds (min ≤ max) & minimum stipend threshold —
        min_sal = cleaned.get('comp_min')
        max_sal = cleaned.get('comp_max')
        if min_sal is not None and max_sal is not None:
            if min_sal > max_sal:
                self.add_error('comp_min', "Min must not exceed max.")
                self.add_error('comp_max', "Max must be ≥ min.")
            # enforce a floor, e.g. at least 100
            if min_sal < 100:
                self.add_error('comp_min', "Minimum stipend must be at least 100.")

        # — Deadline: not in past, not more than 1 year out —
        dl = cleaned.get('application_deadline')
        if dl:
            today = timezone.now().date()
            if dl < today:
                self.add_error('application_deadline', "Deadline cannot be in the past.")
            if dl > today + timedelta(days=365):
                self.add_error('application_deadline', "Deadline cannot be more than one year from now.")

        # — Openings: 1 ≤ openings ≤ 50 —
        openings = cleaned.get('openings')
        if openings is not None:
            if openings < 1 or openings > 50:
                self.add_error('openings', "Openings must be between 1 and 50.")

        return cleaned


class SkillsRequirementsForm(forms.ModelForm):
    class Meta:
        model = InternshipPost
        fields = ['skills','responsibilities','qualifications','benefits']
        widgets = {
          'skills': TagWidget(attrs={'class': 'form-control', 'placeholder': 'e.g. Python, Django'}),
          'responsibilities': CKEditorWidget(),
          'qualifications':   CKEditorWidget(),
          'benefits':         CKEditorWidget(),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Change the label from “Tags” to “Skills”
        self.fields['skills'].label = "Skills"


class ReviewForm(forms.Form):
    # empty form, just to render the final page
    pass


class InternshipPostForm(forms.ModelForm):
    class Meta:
        model = InternshipPost
        # include everything you want editable
        fields = [
            'title', 'city', 'location', 'sector',
            'application_deadline', 'type', 'level',
            'openings', 'comp_min', 'comp_max', 'comp_frequency',
            'skills', 'responsibilities', 'qualifications', 'benefits',
            'is_active',   # allow toggling active/inactive
        ]
        widgets = {
            'title':               forms.TextInput(attrs={'class':'form-control'}),
            'city':                forms.TextInput(attrs={'class':'form-control'}),
            'location':            forms.Select(attrs={'class':'form-select'}),
            'sector':              forms.Select(attrs={'class':'form-select'}),
            'application_deadline':forms.DateInput(attrs={'type':'date','class':'form-control'}),
            'type':                forms.Select(attrs={'class':'form-select'}),
            'level':               forms.Select(attrs={'class':'form-select'}),
            'openings':            forms.NumberInput(attrs={'class':'form-control','min':1}),
            'comp_min':            forms.NumberInput(attrs={'class':'form-control'}),
            'comp_max':            forms.NumberInput(attrs={'class':'form-control'}),
            'comp_frequency':      forms.Select(attrs={'class':'form-select'}),
            'skills':              TagWidget(attrs={'class':'form-control','placeholder':'e.g. Python, Django'}),
            'responsibilities':    CKEditorWidget(),
            'qualifications':      CKEditorWidget(),
            'benefits':            CKEditorWidget(),
            'is_active':           forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }
