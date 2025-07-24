from django import forms
from .models import CompanyProfile, InternshipPost
from django.utils import timezone
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
        min_sal, max_sal = cleaned.get('comp_min'), cleaned.get('comp_max')
        if min_sal and max_sal and min_sal > max_sal:
            self.add_error('comp_min', "Min must not exceed max.")
            self.add_error('comp_max', "Max must be ≥ min.")
        dl = cleaned.get('application_deadline')
        if dl and dl < timezone.now().date():
            self.add_error('application_deadline', "Deadline cannot be in the past.")
        if cleaned.get('openings', 0) < 1:
            self.add_error('openings', "Must have at least one opening.")
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
