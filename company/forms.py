from django import forms
from .models import CompanyProfile

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
