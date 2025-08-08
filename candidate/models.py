from django.db import models
from django.contrib.auth import get_user_model
from ckeditor.fields import RichTextField

User = get_user_model()

PROVINCE_CHOICES = [
    ('1', 'Province No. 1'),
    ('2', 'Province No. 2'),
    ('3', 'Bagmati Province'),
    ('4', 'Gandaki Province'),
    ('5', 'Lumbini Province'),
    ('6', 'Karnali Province'),
    ('7', 'Sudurpashchim Province'),
]

GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
]

EXPERIENCE_LEVEL_CHOICES = [
    ('entry', 'Entry Level (0-2 years)'),
    ('mid', 'Mid Level (3-5 years)'),
    ('senior', 'Senior Level (6-10 years)'),
    ('expert', 'Expert Level (10+ years)'),
]

SOCIAL_PLATFORM_CHOICES = [
    ('github', 'GitHub'),
    ('linkedin', 'LinkedIn'),
    ('twitter', 'Twitter'),
    ('facebook', 'Facebook'),
    ('portfolio', 'Portfolio'),
]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Personal Info
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    about_me = RichTextField(blank=True, config_name='small')

    # Professional Info
    designation = models.CharField(max_length=255, blank=True)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVEL_CHOICES, blank=True)
    sectors = models.TextField(blank=True, help_text="Comma-separated list of sectors")
    skills = models.TextField(blank=True, help_text="Comma-separated list of skills")

    # Address Info
    province = models.CharField(max_length=1, choices=PROVINCE_CHOICES, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    current_address = models.CharField(max_length=255, blank=True)

    # Document uploads
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class SocialLink(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='social_links')
    platform = models.CharField(max_length=20, choices=SOCIAL_PLATFORM_CHOICES)
    url = models.URLField()

    class Meta:
        unique_together = ('profile', 'platform')

    def __str__(self):
        return f"{self.profile.user.username} – {self.platform}"


class Education(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='educations')
    institution = models.CharField(max_length=255)
    degree = models.CharField(max_length=255)
    field_of_study = models.CharField(max_length=255, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    grade = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.degree} at {self.institution}"


class Experience(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='experiences')
    company_name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.role} @ {self.company_name}"


class Project(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=255)
    description = models.TextField()
    technologies = models.TextField(blank=True, help_text="Comma-separated list of technologies")
    project_url = models.URLField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title


class Certificate(models.Model):  # Renamed from Credential
    CERT_TYPE_CHOICES = [
        ('training', 'Training'),
        ('certificate', 'Certificate'),
    ]

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='certificates')
    certificate_type = models.CharField(max_length=20, choices=CERT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    issuer = models.CharField(max_length=255)
    date = models.DateField(null=True, blank=True)
    certificate_url = models.URLField(blank=True)

    def __str__(self):
        return f"{self.title} ({self.get_certificate_type_display()})"
