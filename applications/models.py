from django.db import models
from django.db.models import Q, UniqueConstraint, CheckConstraint
from django.utils import timezone

# Create your models here.
class Application(models.Model):
    """
    One application per candidate per posting (Job OR Internship).
    """
    STATUS_CHOICES = [
        ("applied", "Applied"),
        ("under_review", "Under Review"),
        ("shortlisted", "Shortlisted"),
        ("interview", "Interview"),
        ("offered", "Offered"),
        ("accepted", "Accepted / Hired"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    ]

    # foreign keys (string labels to avoid import cycles)
    candidate       = models.ForeignKey("candidate.Profile", on_delete=models.CASCADE, related_name="applications")
    company         = models.ForeignKey("company.CompanyProfile", on_delete=models.CASCADE, related_name="applications")

    job_post        = models.ForeignKey("company.JobPost", null=True, blank=True, on_delete=models.CASCADE, related_name="applications")
    internship_post = models.ForeignKey("company.InternshipPost", null=True, blank=True, on_delete=models.CASCADE, related_name="applications")

    resume_file     = models.FileField(upload_to="applications/resumes/", null=True, blank=True)
    cover_letter    = models.TextField(blank=True)

    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="applied")
    applied_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_at"]
        constraints = [
            CheckConstraint(
                name="applications_exactly_one_target",
                check=(
                    (Q(job_post__isnull=False) & Q(internship_post__isnull=True)) |
                    (Q(job_post__isnull=True)  & Q(internship_post__isnull=False))
                )
            ),
            
            UniqueConstraint(
                fields=["candidate", "job_post"],
                condition=Q(job_post__isnull=False) & ~Q(status__in=["withdrawn", "rejected"]),
                name="uniq_active_job_application",
            ),
            UniqueConstraint(
                fields=["candidate", "internship_post"],
                condition=Q(internship_post__isnull=False) & ~Q(status__in=["withdrawn", "rejected"]),
                name="uniq_active_intern_application",
            ),
        ]

    def __str__(self):
        return f"{self.candidate} → {self.target_title} ({self.get_status_display()})"

    # Convenience
    @property
    def is_job(self):
        return self.job_post_id is not None

    @property
    def target_title(self):
        if self.is_job:
            return self.job_post.title
        return self.internship_post.title

    @property
    def target_deadline(self):
        if self.is_job:
            return self.job_post.application_deadline
        return self.internship_post.application_deadline

    @property
    def target_is_open(self):
        post = self.job_post if self.is_job else self.internship_post
        return post.is_active and post.application_deadline >= timezone.localdate()


class OfferLetter(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending Candidate Acceptance"),
        ("accepted", "Accepted by Candidate"),
        ("declined", "Declined by Candidate"),
        ("expired", "Expired"),
    ]

    application     = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="offer_letter")
    company         = models.ForeignKey("company.CompanyProfile", on_delete=models.CASCADE, related_name="issued_offers")
    candidate       = models.ForeignKey("candidate.Profile", on_delete=models.CASCADE, related_name="received_offers")

    job_title       = models.CharField(max_length=255)
    offered_salary  = models.CharField(max_length=150, help_text="e.g. NPR 45,000 / month or Paid Internship NPR 15,000/month")
    joining_date    = models.DateField()
    work_location   = models.CharField(max_length=150, default="On-site")
    employment_type = models.CharField(max_length=100, default="Full Time")
    expiration_date = models.DateField(help_text="Last date for candidate to accept the offer")
    
    terms_and_conditions = models.TextField(blank=True, help_text="Specific job duties, working hours, probation period, etc.")
    
    hr_name         = models.CharField("HR / Hiring Manager Name", max_length=150)
    hr_designation  = models.CharField("HR Designation", max_length=150, default="Hiring Manager")
    hr_signature    = models.ImageField(upload_to="offer_letters/signatures/", null=True, blank=True, help_text="Uploaded digital signature image")
    
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    candidate_response_notes = models.TextField(blank=True, null=True)
    accepted_at     = models.DateTimeField(null=True, blank=True)
    
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Offer Letter for {self.candidate} from {self.company.first_name} ({self.get_status_display()})"

    @property
    def is_expired(self):
        if self.status == "pending" and self.expiration_date < timezone.localdate():
            return True
        return False

