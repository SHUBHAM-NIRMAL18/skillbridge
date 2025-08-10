from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import (
    Profile, SocialLink, Education, Experience, Project, Certificate
)
from ckeditor.widgets import CKEditorWidget
from datetime import date
import json
import re

# ---------------- Helpers ----------------
TOKEN_SPLIT_RE = re.compile(r"[,\s]+")

def parse_tokens(value):
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    # try JSON (Tagify can submit arrays)
    try:
        data = json.loads(s)
        if isinstance(data, list):
            tokens = []
            for item in data:
                if isinstance(item, dict) and "value" in item:
                    tokens.append(str(item["value"]).strip())
                else:
                    tokens.append(str(item).strip())
            return [t for t in tokens if t]
    except Exception:
        pass
    # plain text “a, b, c”
    tokens = [t.strip() for t in TOKEN_SPLIT_RE.split(s)]
    return [t for t in tokens if t]

def validate_file_extension(filename, allowed_exts):
    name = filename.lower()
    return any(name.endswith(ext) for ext in allowed_exts)

# ---------------- Base form ----------------
class BaseModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.update({'class': 'form-check-input'})
            elif isinstance(w, forms.RadioSelect):
                w.attrs.update({'class': 'form-check-input'})
            else:
                w.attrs.update({'class': 'form-control'})
                if not isinstance(w, (forms.Select, forms.FileInput)):
                    w.attrs.setdefault('placeholder', field.label or name.replace('_', ' ').title())

# ---------------- Step 1: About ----------------
class PersonalInfoForm(BaseModelForm):
    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'gender', 'date_of_birth', 'about_me']
        widgets = {
            'about_me': CKEditorWidget(config_name='small'),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['gender'].required = True
        self.fields['date_of_birth'].required = True

    def clean_first_name(self):
        first_name = (self.cleaned_data.get('first_name') or '').strip()
        if any(ch.isdigit() for ch in first_name):
            raise ValidationError("First name cannot contain numbers.")
        return first_name

    def clean_last_name(self):
        last_name = (self.cleaned_data.get('last_name') or '').strip()
        if any(ch.isdigit() for ch in last_name):
            raise ValidationError("Last name cannot contain numbers.")
        return last_name

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > date.today():
            raise ValidationError("Date of birth cannot be in the future.")
        if dob and (date.today().year - dob.year) < 16:
            raise ValidationError("You must be at least 16 years old.")
        return dob

# ---------------- Step 2: Professional ----------------
class ProfessionalInfoForm(BaseModelForm):
    sectors = forms.CharField(
        widget=forms.TextInput(attrs={'data-role': 'tagsinput'}),
        required=True, help_text="Add multiple sectors separated by commas"
    )
    skills = forms.CharField(
        widget=forms.TextInput(attrs={'data-role': 'tagsinput'}),
        required=True, help_text="Add multiple skills separated by commas"
    )

    class Meta:
        model = Profile
        fields = ['designation', 'experience_level', 'sectors', 'skills']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['designation'].required = True
        self.fields['experience_level'].required = True

    def clean_sectors(self):
        tokens = parse_tokens(self.cleaned_data.get('sectors'))
        if not tokens:
            raise ValidationError("Please add at least one sector.")
        return ", ".join(tokens)

    def clean_skills(self):
        tokens = parse_tokens(self.cleaned_data.get('skills'))
        if not tokens:
            raise ValidationError("Please add at least one skill.")
        return ", ".join(tokens)

# ---------------- Step 3: Contact/Address ----------------
PHONE_RE = re.compile(r"^\+?\d[\d\-\s]{6,}$")

class AddressInfoForm(BaseModelForm):
    class Meta:
        model = Profile
        fields = ['phone_number', 'province', 'city', 'postal_code', 'current_address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone_number'].required = True
        self.fields['province'].required = True
        self.fields['city'].required = True

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not PHONE_RE.match(phone):
            raise ValidationError("Please enter a valid phone number.")
        return phone

# ---------------- Step 4: Education (min 1) ----------------
class EducationForm(BaseModelForm):
    class Meta:
        model = Education
        fields = ['institution', 'degree', 'field_of_study', 'start_date', 'end_date', 'grade']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['institution'].required = True
        self.fields['degree'].required = True
        self.fields['start_date'].required = True

    def clean(self):
        cleaned = super().clean()
        sd, ed = cleaned.get('start_date'), cleaned.get('end_date')
        if ed and sd and ed < sd:
            raise ValidationError("End date cannot be before start date.")
        return cleaned

EducationFormSet = inlineformset_factory(
    Profile, Education, form=EducationForm,
    extra=0, can_delete=True, can_order=False,
    min_num=1, validate_min=True
)

# ---------------- Step 5: Experience (optional if entry) ----------------
class ExperienceForm(BaseModelForm):
    description = forms.CharField(widget=CKEditorWidget(config_name='small'), required=False)

    class Meta:
        model = Experience
        fields = ['company_name', 'role', 'location', 'start_date', 'end_date', 'is_current', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company_name'].required = True
        self.fields['role'].required = True
        self.fields['start_date'].required = True

    def clean(self):
        cleaned = super().clean()
        sd, ed, current = cleaned.get('start_date'), cleaned.get('end_date'), cleaned.get('is_current')
        if not current and ed and sd and ed < sd:
            raise ValidationError("End date cannot be before start date.")
        if current and ed:
            raise ValidationError("Current job shouldn't have an end date.")
        return cleaned

ExperienceFormSet = inlineformset_factory(
    Profile, Experience, form=ExperienceForm,
    extra=0, can_delete=True, can_order=False,
    min_num=0, validate_min=False
)

# ---------------- Step 6: Projects (min 1) ----------------
class ProjectForm(BaseModelForm):
    technologies = forms.CharField(
        widget=forms.TextInput(attrs={'data-role': 'tagsinput'}),
        required=False, help_text="Add multiple technologies separated by commas"
    )
    description = forms.CharField(widget=CKEditorWidget(config_name='small'), required=True)

    class Meta:
        model = Project
        fields = ['title', 'description', 'technologies', 'project_url', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = True

    def clean(self):
        cleaned = super().clean()
        sd, ed = cleaned.get('start_date'), cleaned.get('end_date')
        if ed and sd and ed < sd:
            raise ValidationError("End date cannot be before start date.")
        raw = cleaned.get('technologies')
        if raw:
            cleaned['technologies'] = ", ".join(parse_tokens(raw))
        return cleaned

ProjectFormSet = inlineformset_factory(
    Profile, Project, form=ProjectForm,
    extra=0, can_delete=True, can_order=False,
    min_num=1, validate_min=True
)

# ---------------- Step 7: Certificates (optional) ----------------
class CertificateForm(BaseModelForm):
    class Meta:
        model = Certificate
        fields = ['certificate_type', 'title', 'issuer', 'date', 'certificate_url']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

CertificateFormSet = inlineformset_factory(
    Profile, Certificate, form=CertificateForm,
    extra=0, can_delete=True, can_order=False,
    min_num=0, validate_min=False
)

# ---------------- Step 8: Social (min 1; must include LinkedIn/GitHub) ----------------
class SocialLinkForm(BaseModelForm):
    class Meta:
        model = SocialLink
        fields = ['platform', 'url']

    def clean_url(self):
        url = self.cleaned_data.get('url')
        URLValidator()(url)
        platform = self.cleaned_data.get('platform')
        if platform == 'linkedin' and 'linkedin.com' not in url:
            raise ValidationError("Please enter a valid LinkedIn URL.")
        if platform == 'github' and 'github.com' not in url:
            raise ValidationError("Please enter a valid GitHub URL.")
        if platform == 'twitter' and 'twitter.com' not in url:
            raise ValidationError("Please enter a valid Twitter URL.")
        return url

class SocialLinkInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen, has_li_or_gh = set(), False
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or form.cleaned_data.get('DELETE'):
                continue
            platform = form.cleaned_data.get('platform')
            url = form.cleaned_data.get('url')
            if not platform and not url:
                continue
            if platform in seen:
                raise ValidationError("You already added this platform.")
            seen.add(platform)
            if platform in ('linkedin', 'github'):
                has_li_or_gh = True
        if not has_li_or_gh:
            raise ValidationError("Please add at least one LinkedIn or GitHub link.")

SocialLinkFormSet = inlineformset_factory(
    Profile, SocialLink,
    form=SocialLinkForm, formset=SocialLinkInlineFormSet,
    extra=0, can_delete=True, can_order=False,
    min_num=1, validate_min=True
)

# ---------------- Step 9: Documents ----------------
class DocumentUploadForm(BaseModelForm):
    class Meta:
        model = Profile
        fields = ['profile_picture', 'resume']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'resume': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_profile_picture(self):
        image = self.cleaned_data.get('profile_picture')
        if image:
            if image.size > 2 * 1024 * 1024:
                raise ValidationError("Profile picture too large (max 2MB).")
            if not validate_file_extension(image.name, ('.jpg', '.jpeg', '.png')):
                raise ValidationError("Only JPG/PNG images are allowed.")
        return image

    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if not resume:
            raise ValidationError("Please upload your resume (PDF/DOC/DOCX).")
        if resume.size > 5 * 1024 * 1024:
            raise ValidationError("Resume too large (max 5MB).")
        if not validate_file_extension(resume.name, ('.pdf', '.doc', '.docx')):
            raise ValidationError("Only PDF, DOC, or DOCX files are allowed.")
        return resume
