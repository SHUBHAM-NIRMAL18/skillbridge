from django.db import models
from django.contrib.auth import get_user_model
from taggit.managers import TaggableManager
from django.utils import timezone

User = get_user_model()

# Create your models here.


PROVINCE_CHOICES = [
    ("Koshi",        "Koshi (Province No.1)"),
    ("Madhesh",      "Madhesh (Province No.2)"),
    ("Bagmati",      "Bagmati (Province No.3)"),
    ("Gandaki",      "Gandaki (Province No.4)"),
    ("Lumbini",      "Lumbini (Province No.5)"),
    ("Karnali",      "Karnali (Province No.6)"),
    ("Sudurpashchim","Sudurpashchim (Province No.7)"),
]

COMPANY_SIZE_CHOICES = [
    ("1-10",   "1–10 employees"),
    ("11-50",  "11–50 employees"),
    ("51-200", "51–200 employees"),
    ("201-500","201–500 employees"),
    ("501-1000","501–1000 employees"),
    ("1001+",  "1001+ employees"),
]

class CompanyProfile(models.Model):
    logo = models.ImageField(
        upload_to='company_logos/',
        blank=True,
        null=True,
        help_text="Upload a square PNG/JPG up to 2-MB"
    )
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name="company_profile")
    first_name      = models.CharField("First Name", max_length=150)
    last_name       = models.CharField("Last Name",  max_length=150)
    industry        = models.CharField(max_length=100)
    founded_date    = models.DateField()
    company_size    = models.CharField(max_length=20, choices=COMPANY_SIZE_CHOICES)
    about_company   = models.TextField()
    phone           = models.CharField("Phone Number", max_length=20)
    website_url     = models.URLField("Website URL", blank=True, null=True)

    # now a dropdown of 7 provinces:
    province        = models.CharField(max_length=20, choices=PROVINCE_CHOICES)
    # free‐text city:
    city            = models.CharField("City", max_length=100)

    postal_code     = models.CharField(max_length=20)
    current_address = models.CharField(max_length=255)
    social_link     = models.URLField("Social Link", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company Profile"
        verbose_name_plural = "Company Profiles"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.industry})"

    @property
    def email(self):
        return self.user.email



class InternshipPost(models.Model):
    
    LOCATION_CHOICES = [
        ("Onsite",  "Onsite"),
        ("Remote",  "Remote"),
        ("Hybrid",  "Hybrid"),
    ]
    TYPE_CHOICES = [
        ("Full‑Time", "Full‑Time"),
        ("Part‑Time", "Part‑Time"),
        ("Contract",  "Contract"),
    ]
    LEVEL_CHOICES = [
        ("Entry", "Entry"),
        ("Mid",   "Mid"),
        ("Senior","Senior"),
    ]
    FREQUENCY_CHOICES = [
        ("Hourly",  "Hourly"),
        ("Daily",   "Daily"),
        ("Monthly", "Monthly"),
    ]
    SECTOR_CHOICES = [
        ("Web Development", "Web Development"),
        ("UI/UX",           "UI/UX"),
        ("Marketing",       "Marketing"),
        ("Data Science",    "Data Science"),
        # …add as needed…
    ]

    company               = models.ForeignKey(
        "company.CompanyProfile",
        on_delete=models.CASCADE,
        related_name="internships"
    )
    # — Basic Details —
    title                 = models.CharField(max_length=100)
    city                  = models.CharField(max_length=100)
    location              = models.CharField(max_length=10, choices=LOCATION_CHOICES)
    sector                = models.CharField(max_length=50, choices=SECTOR_CHOICES)
    application_deadline  = models.DateField()
    type                  = models.CharField(max_length=20, choices=TYPE_CHOICES)
    level                 = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)
    openings              = models.PositiveIntegerField()
    comp_min              = models.PositiveIntegerField(verbose_name="Min Salary")
    comp_max              = models.PositiveIntegerField(verbose_name="Max Salary")
    comp_frequency        = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)

    # — Skills & Requirements —
    skills = TaggableManager(
        verbose_name="Skills",
        help_text="A comma-separated list of skills.",
        blank=True
    )
    responsibilities      = models.TextField(blank=True)
    qualifications        = models.TextField(blank=True)
    benefits              = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} at {self.company}"
    
    @property
    def status(self):
        if not self.is_active:
           return "Inactive"
        return "Active" if self.application_deadline >= timezone.now().date() else "Closed"
    
    @property
    def days_left(self):
        """How many days remain until the deadline."""
        delta = self.application_deadline - timezone.localdate()
        return max(delta.days, 0)
    
class JobPost(models.Model):
    LOCATION_CHOICES = [
        ("Onsite",  "Onsite"),
        ("Remote",  "Remote"),
        ("Hybrid",  "Hybrid"),
    ]
    TYPE_CHOICES = [
        ("Full Time",  "Full Time"),
        ("Part Time",  "Part Time"),
        ("Internship", "Internship"),
        ("Contract",   "Contract"),
    ]
    LEVEL_CHOICES = [
        ("Entry",  "Entry"),
        ("Mid",    "Mid"),
        ("Senior", "Senior"),
        ("Lead",   "Lead"),
    ]
    EXPERIENCE_UNIT_CHOICES = [
        ("Years",  "Years"),
        ("Months", "Months"),
    ]
    SALARY_PERIOD_CHOICES = [
        ("Monthly", "Monthly"),
        ("Yearly",  "Yearly"),
    ]
    SECTOR_CHOICES = [
        ("IT",         "IT"),
        ("Finance",    "Finance"),
        ("Marketing",  "Marketing"),
        ("Design",     "Design"),
        ("Data",       "Data"),
        ("Healthcare", "Healthcare"),
        ("Education",  "Education"),

    ]

    company              = models.ForeignKey(
        CompanyProfile,
        on_delete=models.CASCADE,
        related_name="job_posts"
    )
    title                = models.CharField(max_length=150)
    province             = models.CharField(max_length=20, choices=PROVINCE_CHOICES)
    city                 = models.CharField(max_length=100)
    location_type        = models.CharField(max_length=10, choices=LOCATION_CHOICES)
    sector               = models.CharField(max_length=50, choices=SECTOR_CHOICES)
    application_deadline = models.DateField()

    job_type             = models.CharField(max_length=20, choices=TYPE_CHOICES)
    job_level            = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    experience_required  = models.PositiveIntegerField()
    experience_unit      = models.CharField(max_length=10, choices=EXPERIENCE_UNIT_CHOICES)
    openings             = models.PositiveIntegerField()
    salary_min           = models.DecimalField(max_digits=10, decimal_places=2)
    salary_max           = models.DecimalField(max_digits=10, decimal_places=2)
    salary_period        = models.CharField(max_length=10, choices=SALARY_PERIOD_CHOICES)


    responsibilities     = models.TextField(blank=True)
    skills               = TaggableManager(blank=True)
    qualifications       = models.TextField(blank=True)
    benefits             = models.TextField(blank=True)

    is_active            = models.BooleanField(default=True)
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} at {self.company}"

    @property
    def status(self):
        if not self.is_active:
            return "Inactive"
        return "Active" if self.application_deadline >= timezone.localdate() else "Closed"

    @property
    def days_left(self):
        delta = self.application_deadline - timezone.localdate()
        return max(delta.days, 0)