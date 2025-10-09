from django import forms
from .models import CompanyProfile, InternshipPost, JobPost, PROVINCE_CHOICES, Sector
from django.utils import timezone
from datetime import timedelta
import re
from ckeditor.widgets import CKEditorWidget
from taggit.forms import TagWidget
from django.contrib.auth.forms import PasswordChangeForm
from urllib.parse import urlparse
from datetime import date, timedelta


# ---- helpers: dynamic sector choices with safe fallback ----
DEFAULT_JOB_SECTORS = ["IT", "Finance", "Marketing", "Design", "Data", "Healthcare", "Education"]
DEFAULT_INTERNSHIP_SECTORS = ["Web Development", "UI/UX", "Marketing", "Data Science"]

def sector_choices_or_fallback(default_names):
    # Read active sectors from DB; if none exist, fall back to defaults
    names = list(Sector.objects.filter(is_active=True).order_by("display_order", "name").values_list("name", flat=True))
    if not names:
        names = default_names
    # Include an empty prompt; field is required, so empty will fail validation if submitted
    return [("", "Select sector")] + [(n, n) for n in names]


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = [
            'first_name', 'last_name', 'industry', 'founded_date',
            'company_size', 'about_company', 'phone', 'website_url',
            'province', 'city', 'postal_code', 'current_address',
            'social_link', 'logo',
        ]
        labels = {
            'first_name': 'Company First Name',
            'last_name': 'Company Last Name',
            'industry': 'Business Industry',
            'founded_date': 'Date Established',
            'company_size': 'Number of Employees',
            'about_company': 'Company Description',
            'website_url': 'Company Website',
            'social_link': 'Social Media Profile',
        }
        widgets = {
            'first_name':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'industry':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Industry'}),
            'founded_date':    forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'company_size':    forms.Select(attrs={'class': 'form-select'}),
            'about_company':   forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us about your company…'}),
            'logo':            forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'phone':           forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'website_url':     forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
            'province':        forms.Select(attrs={'class': 'form-select'}),
            'city':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'postal_code':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
            'current_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current Address'}),
            'social_link':     forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
        }

    # --- Individual field validations ---
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not first_name:
            raise forms.ValidationError("Company first name is required.")

        # Allow letters and spaces only
        if not re.match(r'^[A-Za-z\s]+$', first_name):
            raise forms.ValidationError("First name must contain only letters and spaces.")

        return first_name


    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not last_name:
            raise forms.ValidationError("Company last name is required.")

        # Allow letters and spaces only
        if not re.match(r'^[A-Za-z\s]+$', last_name):
            raise forms.ValidationError("Last name must contain only letters and spaces.")

        return last_name

    def clean_industry(self):
        industry = self.cleaned_data.get('industry', '').strip()
        if not industry:
            raise forms.ValidationError("Business industry is required.")
        return industry

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits long.")
        return phone

    def clean_postal_code(self):
        postal_code = self.cleaned_data.get('postal_code', '').strip()
        if not postal_code:
            raise forms.ValidationError("Postal code is required.")
        if not postal_code.isdigit():
            raise forms.ValidationError("Postal code must contain only digits.")
        if len(postal_code) not in [5, 6]:
            raise forms.ValidationError("Postal code must be 5 or 6 digits long.")
        return postal_code

    def clean_website_url(self):
        website_url = self.cleaned_data.get('website_url', '').strip()
        if website_url:
            parsed = urlparse(website_url)
            if not all([parsed.scheme, parsed.netloc]):
                raise forms.ValidationError("Enter a valid website URL (e.g., https://example.com).")
        return website_url

    def clean_social_link(self):
        social_link = self.cleaned_data.get('social_link', '').strip()
        if social_link:
            parsed = urlparse(social_link)
            if not all([parsed.scheme, parsed.netloc]):
                raise forms.ValidationError("Enter a valid social media link (e.g., https://linkedin.com/company/yourcompany).")
        return social_link

    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()
        if not city:
            raise forms.ValidationError("City is required.")
        if not re.match(r"^[a-zA-Z\s]+$", city):
            raise forms.ValidationError("City name must contain only letters.")
        return city

    def clean_current_address(self):
        current_address = self.cleaned_data.get('current_address', '').strip()
        if not current_address:
            raise forms.ValidationError("Current address is required.")
        return current_address
    
    def clean_founded_date(self):
        founded_date = self.cleaned_data.get('founded_date')

        if not founded_date:
            raise forms.ValidationError("Founded date is required.")

        today = date.today()

        # Disallow future dates
        if founded_date > today:
            raise forms.ValidationError("Founded date cannot be in the future.")

        # Disallow today's date
        if founded_date == today:
            raise forms.ValidationError("Founded date cannot be today.")

        # Disallow dates older than 50 years
        fifty_years_ago = today.replace(year=today.year - 50)
        if founded_date < fifty_years_ago:
            raise forms.ValidationError("Founded date cannot be more than 50 years in the past.")

        return founded_date



class BasicDetailsForm(forms.ModelForm):
    class Meta:
        model = InternshipPost
        fields = [
            'title', 'city', 'location', 'sector',
            'application_deadline', 'type', 'level',
            'openings', 'comp_min', 'comp_max', 'comp_frequency',
        ]
        widgets = {
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rebind as ChoiceField to enforce validation against dynamic list
        self.fields['sector'] = forms.ChoiceField(
            choices=sector_choices_or_fallback(DEFAULT_INTERNSHIP_SECTORS),
            widget=forms.Select(attrs={'class': 'form-select'}),
            required=True,
            label="Sector"
        )

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
        self.fields['skills'].label = "Skills"


class ReviewForm(forms.Form):
    # empty form, just to render the final page
    pass


class InternshipPostForm(forms.ModelForm):
    class Meta:
        model = InternshipPost
        fields = [
            'title', 'city', 'location', 'sector',
            'application_deadline', 'type', 'level',
            'openings', 'comp_min', 'comp_max', 'comp_frequency',
            'skills', 'responsibilities', 'qualifications', 'benefits',
            'is_active',
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sector'] = forms.ChoiceField(
            choices=sector_choices_or_fallback(DEFAULT_INTERNSHIP_SECTORS),
            widget=forms.Select(attrs={'class': 'form-select'}),
            required=True,
            label="Sector"
        )


class JobBasicDetailsForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = [
            'title', 'province', 'city',
            'location_type', 'sector', 'application_deadline',
            'job_type', 'job_level',
            'experience_required', 'experience_unit',
            'openings', 'salary_min', 'salary_max', 'salary_period',
        ]
        widgets = {
            'title':               forms.TextInput(attrs={'class': 'form-control','placeholder': 'Job title (min 5 chars)'}),
            'province':            forms.Select(attrs={'class': 'form-select'}),
            'city':                forms.TextInput(attrs={'class': 'form-control','placeholder': 'City'}),
            'location_type':       forms.Select(attrs={'class': 'form-select'}),
            'sector':              forms.Select(attrs={'class': 'form-select'}),
            'application_deadline':forms.DateInput(attrs={'type': 'date','class': 'form-control'}),
            'job_type':            forms.Select(attrs={'class': 'form-select'}),
            'job_level':           forms.Select(attrs={'class': 'form-select'}),
            'experience_required': forms.NumberInput(attrs={'class': 'form-control','min': 0}),
            'experience_unit':     forms.Select(attrs={'class': 'form-select'}),
            'openings':            forms.NumberInput(attrs={'class': 'form-control','min': 1}),
            'salary_min':          forms.NumberInput(attrs={'class': 'form-control','placeholder': 'Min salary'}),
            'salary_max':          forms.NumberInput(attrs={'class': 'form-control','placeholder': 'Max salary'}),
            'salary_period':       forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sector'] = forms.ChoiceField(
            choices=sector_choices_or_fallback(DEFAULT_JOB_SECTORS),
            widget=forms.Select(attrs={'class': 'form-select'}),
            required=True,
            label="Sector"
        )

    def clean(self):
        cleaned = super().clean()

        # Title length
        title = cleaned.get('title', '').strip()
        if title:
            cleaned['title'] = title
            if len(title) < 5:
                self.add_error('title', 'Title must be at least 5 characters.')

        # City format
        city = cleaned.get('city', '').strip()
        if city:
            cleaned['city'] = city
            if not re.match(r'^[A-Za-z\s\-]+$', city):
                self.add_error('city', 'City may only contain letters, spaces, or hyphens.')

        # Deadline: future & ≤ 1 year out
        dl = cleaned.get('application_deadline')
        if dl:
            today = timezone.localdate()
            if dl < today:
                self.add_error('application_deadline', 'Deadline cannot be in the past.')
            if dl > today + timedelta(days=365):
                self.add_error('application_deadline', 'Deadline cannot exceed one year from today.')

        # Salary bounds
        min_sal = cleaned.get('salary_min')
        max_sal = cleaned.get('salary_max')
        if min_sal is not None and max_sal is not None:
            if min_sal > max_sal:
                self.add_error('salary_min', 'Min salary must not exceed max salary.')
                self.add_error('salary_max', 'Max salary must be at least min salary.')
            if min_sal < 0:
                self.add_error('salary_min', 'Salary must be non-negative.')

        # Openings
        opens = cleaned.get('openings')
        if opens is not None and opens < 1:
            self.add_error('openings', 'You must have at least one opening.')

        # Experience
        exp = cleaned.get('experience_required')
        if exp is not None and exp < 0:
            self.add_error('experience_required', 'Experience cannot be negative.')

        return cleaned


class JobSkillsRequirementsForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = ['skills', 'responsibilities', 'qualifications', 'benefits']
        widgets = {
            'skills':          TagWidget(attrs={'class': 'form-control','placeholder': 'e.g. Python, Django'}),
            'responsibilities':CKEditorWidget(),
            'qualifications':  CKEditorWidget(),
            'benefits':        CKEditorWidget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skills'].label = "Skills"


class JobReviewForm(forms.Form):
    confirm = forms.BooleanField(
        label="I confirm that all information above is correct.",
        required=True
    )


class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = [
            'title', 'province', 'city',
            'location_type', 'sector', 'application_deadline',
            'job_type', 'job_level',
            'experience_required', 'experience_unit',
            'openings', 'salary_min', 'salary_max', 'salary_period',
            'skills', 'responsibilities', 'qualifications', 'benefits',
            'is_active',
        ]
        widgets = {
            'title':               forms.TextInput(attrs={'class': 'form-control'}),
            'province':            forms.Select(attrs={'class': 'form-select'}),
            'city':                forms.TextInput(attrs={'class': 'form-control'}),
            'location_type':       forms.Select(attrs={'class': 'form-select'}),
            'sector':              forms.Select(attrs={'class': 'form-select'}),
            'application_deadline':forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'job_type':            forms.Select(attrs={'class': 'form-select'}),
            'job_level':           forms.Select(attrs={'class': 'form-select'}),
            'experience_required': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'experience_unit':     forms.Select(attrs={'class': 'form-select'}),
            'openings':            forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'salary_min':          forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min salary'}),
            'salary_max':          forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max salary'}),
            'salary_period':       forms.Select(attrs={'class': 'form-select'}),
            'skills':              TagWidget(attrs={'class': 'form-control', 'placeholder': 'e.g. Python, Django'}),
            'responsibilities':    CKEditorWidget(),
            'qualifications':      CKEditorWidget(),
            'benefits':            CKEditorWidget(),
            'is_active':           forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sector'] = forms.ChoiceField(
            choices=sector_choices_or_fallback(DEFAULT_JOB_SECTORS),
            widget=forms.Select(attrs={'class': 'form-select'}),
            required=True,
            label="Sector"
        )


class NotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = ['notify_all', 'notify_on_message', 'notify_on_application']
        widgets = {
            'notify_all':            forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'notify_on_message':     forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'notify_on_application': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }
        labels = {
            'notify_all':            "All notifications",
            'notify_on_message':     "Notify me when someone messages",
            'notify_on_application': "Notify me when someone applies",
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to each field
        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': field.label,
            })
