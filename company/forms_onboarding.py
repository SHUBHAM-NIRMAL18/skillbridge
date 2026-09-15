from django import forms
from urllib.parse import urlparse
from .models import CompanyProfile, PROVINCE_CHOICES, COMPANY_SIZE_CHOICES

class CompanyOnboardingForm(forms.ModelForm):
    # Step 1: Identity & Brand
    first_name = forms.CharField(
        max_length=150,
        label="Company Name",
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. CloudTech Innovations',
            'id': 'id_first_name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        label="Company Suffix / Subtitle",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Pvt. Ltd. / Nepal Branch',
            'id': 'id_last_name'
        })
    )
    industry = forms.CharField(
        max_length=100,
        label="Industry / Domain",
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Software & Technology, Fintech, Healthcare',
            'id': 'id_industry'
        })
    )
    company_size = forms.ChoiceField(
        choices=[('', 'Select Company Size')] + COMPANY_SIZE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'id_company_size'})
    )
    founded_date = forms.DateField(
        label="Date Established",
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-lg', 'id': 'id_founded_date'})
    )
    logo = forms.ImageField(
        label="Company Logo",
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'id': 'id_logo'})
    )

    # Step 2: Location & Contact
    province = forms.ChoiceField(
        choices=[('', 'Select Province')] + PROVINCE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'id_province'})
    )
    city = forms.CharField(
        max_length=100,
        label="City",
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Kathmandu, Lalitpur, Pokhara',
            'id': 'id_city'
        })
    )
    postal_code = forms.CharField(
        max_length=20,
        label="Postal Code",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. 44600',
            'id': 'id_postal_code'
        })
    )
    current_address = forms.CharField(
        max_length=255,
        label="Office Address",
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. Lazimpat Rd, Ward 2',
            'id': 'id_current_address'
        })
    )
    phone = forms.CharField(
        max_length=20,
        label="Business Phone",
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. 9812345678 or 01-4455667',
            'id': 'id_phone'
        })
    )
    website_url = forms.CharField(
        max_length=255,
        label="Website URL",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'https://yourcompany.com',
            'id': 'id_website_url'
        })
    )

    # Step 3: Culture & Social
    about_company = forms.CharField(
        label="About the Company",
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Share your company mission, workplace culture, and what excites candidates about joining your team...',
            'id': 'id_about_company'
        })
    )
    social_link = forms.CharField(
        max_length=255,
        label="Company LinkedIn / Social Page",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'https://linkedin.com/company/yourbrand',
            'id': 'id_social_link'
        })
    )
    notify_on_application = forms.BooleanField(
        required=False,
        initial=True,
        label="Receive instant email notifications when candidates apply",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_notify_on_application'})
    )

    class Meta:
        model = CompanyProfile
        fields = [
            'first_name', 'last_name', 'industry', 'company_size', 'founded_date', 'logo',
            'province', 'city', 'postal_code', 'current_address', 'phone', 'website_url',
            'about_company', 'social_link', 'notify_on_application',
        ]

    def _clean_url(self, field_name):
        val = self.cleaned_data.get(field_name)
        if not val:
            return None
        val = val.strip()
        if not val:
            return None
        parsed = urlparse(val)
        if not parsed.scheme:
            val = "https://" + val
            parsed = urlparse(val)
        if not parsed.netloc:
            raise forms.ValidationError("Enter a valid URL.")
        return val

    def clean_website_url(self):
        return self._clean_url('website_url')

    def clean_social_link(self):
        return self._clean_url('social_link')

    def clean_last_name(self):
        val = self.cleaned_data.get('last_name')
        if not val:
            return "Company"
        return val.strip()

    def clean_postal_code(self):
        val = self.cleaned_data.get('postal_code')
        if not val:
            return "00000"
        return val.strip()
