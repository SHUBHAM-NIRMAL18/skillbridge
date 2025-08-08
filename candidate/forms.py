from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.forms import inlineformset_factory
from .models import (
    Profile, SocialLink, Education, Experience, Project, Certificate
)
from ckeditor.widgets import CKEditorWidget
from datetime import date

# ————————————————————————————————
# Base form customizations
# ————————————————————————————————
class BaseModelForm(forms.ModelForm):
    """
    - Adds Bootstrap classes
    - Adds a placeholder equal to the field's label (nice UX)
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(widget, forms.RadioSelect):
                widget.attrs.update({'class': 'form-check-input'})
            else:
                widget.attrs.update({'class': 'form-control'})
                # set placeholder unless it's a file or select
                if not isinstance(widget, (forms.Select, forms.FileInput)):
                    widget.attrs.setdefault('placeholder', field.label or name.replace('_', ' ').title())

# ————————————————————————————————
# Step 1: Personal Information
# ————————————————————————————————
class PersonalInfoForm(BaseModelForm):
    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'email', 'phone_number',
                  'gender', 'date_of_birth', 'about_me']
        widgets = {
            'about_me': CKEditorWidget(config_name='small'),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > date.today():
            raise ValidationError("Date of birth cannot be in the future")
        if dob and (date.today().year - dob.year) < 16:
            raise ValidationError("You must be at least 16 years old")
        return dob

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not phone.isdigit():
            raise ValidationError("Phone number should contain only digits")
        return phone

# ————————————————————————————————
# Step 2: Professional Information
# ————————————————————————————————
class ProfessionalInfoForm(BaseModelForm):
    sectors = forms.CharField(
        widget=forms.TextInput(attrs={'data-role': 'tagsinput'}),
        required=False,
        help_text="Add multiple sectors separated by commas"
    )
    skills = forms.CharField(
        widget=forms.TextInput(attrs={'data-role': 'tagsinput'}),
        required=False,
        help_text="Add multiple skills separated by commas"
    )

    class Meta:
        model = Profile
        fields = ['designation', 'experience_level', 'sectors', 'skills']

# ————————————————————————————————
# Step 3: Address Information
# ————————————————————————————————
class AddressInfoForm(BaseModelForm):
    class Meta:
        model = Profile
        fields = ['province', 'city', 'postal_code', 'current_address']

# ————————————————————————————————
# Step 4: Education (Inline Formset)
# ————————————————————————————————
class EducationForm(BaseModelForm):
    class Meta:
        model = Education
        fields = ['institution', 'degree', 'field_of_study',
                  'start_date', 'end_date', 'grade']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        sd = cleaned.get('start_date')
        ed = cleaned.get('end_date')
        if ed and sd and ed < sd:
            raise ValidationError("End date cannot be before start date")
        return cleaned

EducationFormSet = inlineformset_factory(
    Profile, Education, form=EducationForm,
    extra=1, can_delete=True, can_order=False,
    min_num=1, validate_min=True      # 👉 require at least one education
)

# ————————————————————————————————
# Step 5: Experience (Inline Formset)
# ————————————————————————————————
class ExperienceForm(BaseModelForm):
    description = forms.CharField(
        widget=CKEditorWidget(config_name='small'),
        required=False
    )

    class Meta:
        model = Experience
        fields = ['company_name', 'role', 'location',
                  'start_date', 'end_date', 'is_current', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        sd = cleaned.get('start_date')
        ed = cleaned.get('end_date')
        current = cleaned.get('is_current')

        if not current and ed and sd and ed < sd:
            raise ValidationError("End date cannot be before start date")
        if current and ed:
            raise ValidationError("Current job shouldn't have an end date")
        return cleaned

ExperienceFormSet = inlineformset_factory(
    Profile, Experience, form=ExperienceForm,
    extra=1, can_delete=True, can_order=False,
    min_num=1, validate_min=True      # 👉 require at least one experience
)

# ————————————————————————————————
# Step 6: Projects (Inline Formset)
# ————————————————————————————————
class ProjectForm(BaseModelForm):
    technologies = forms.CharField(
        widget=forms.TextInput(attrs={'data-role': 'tagsinput'}),
        required=False,
        help_text="Add multiple technologies separated by commas"
    )

    # Use CKEditor for project description for consistency
    description = forms.CharField(
        widget=CKEditorWidget(config_name='small'),
        required=False
    )

    class Meta:
        model = Project
        fields = ['title', 'description', 'technologies',
                  'project_url', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        sd = cleaned.get('start_date')
        ed = cleaned.get('end_date')
        if ed and sd and ed < sd:
            raise ValidationError("End date cannot be before start date")
        return cleaned

ProjectFormSet = inlineformset_factory(
    Profile, Project, form=ProjectForm,
    extra=1, can_delete=True, can_order=False,
    min_num=0, validate_min=False     # tweak if you want at least one project
)

# ————————————————————————————————
# Step 7: Certificates (Inline Formset)
# ————————————————————————————————
class CertificateForm(BaseModelForm):
    class Meta:
        model = Certificate
        fields = ['certificate_type', 'title', 'issuer', 'date', 'certificate_url']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

CertificateFormSet = inlineformset_factory(
    Profile, Certificate, form=CertificateForm,
    extra=1, can_delete=True, can_order=False,
    min_num=0, validate_min=False
)

# ————————————————————————————————
# Step 8: Social Links (Inline Formset)
# ————————————————————————————————
class SocialLinkForm(BaseModelForm):
    class Meta:
        model = SocialLink
        fields = ['platform', 'url']

    def clean_url(self):
        url = self.cleaned_data.get('url')
        validator = URLValidator()
        try:
            validator(url)
        except ValidationError:
            raise ValidationError("Please enter a valid URL")

        platform = self.cleaned_data.get('platform')
        if platform == 'linkedin' and 'linkedin.com' not in url:
            raise ValidationError("Please enter a valid LinkedIn URL")
        if platform == 'github' and 'github.com' not in url:
            raise ValidationError("Please enter a valid GitHub URL")
        if platform == 'twitter' and 'twitter.com' not in url:
            raise ValidationError("Please enter a valid Twitter URL")
        return url

SocialLinkFormSet = inlineformset_factory(
    Profile, SocialLink, form=SocialLinkForm,
    extra=1, can_delete=True, can_order=False,
    min_num=0, validate_min=False
)

# ————————————————————————————————
# Step 9: Document Uploads
# ————————————————————————————————
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
                raise ValidationError("Profile picture too large (max 2MB)")
            if not image.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                raise ValidationError("Only JPG/PNG images are allowed")
        return image

    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            if not resume.name.lower().endswith('.pdf'):
                raise ValidationError("Only PDF files are allowed")
            if resume.size > 5 * 1024 * 1024:
                raise ValidationError("Resume too large (max 5MB)")
        return resume
