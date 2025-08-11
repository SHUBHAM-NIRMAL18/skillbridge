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
