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


class Interview(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("confirmed", "Confirmed by Candidate"),
        ("reschedule_requested", "Reschedule Requested"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    TYPE_CHOICES = [
        ("video", "Online Video Call"),
        ("in_person", "In-Person"),
        ("phone", "Phone Screening"),
    ]

    ROUND_CHOICES = [
        ("Screening Call", "Screening Call"),
        ("Technical Interview", "Technical Interview"),
        ("System Design", "System Design"),
        ("HR & Culture Fit", "HR & Culture Fit"),
        ("Managerial Round", "Managerial Round"),
        ("Final Interview", "Final Interview"),
    ]

    application = models.ForeignKey(
        Application, 
        on_delete=models.CASCADE, 
        related_name="interviews"
    )
    company = models.ForeignKey(
        "company.CompanyProfile", 
        on_delete=models.CASCADE, 
        related_name="scheduled_interviews"
    )
    candidate = models.ForeignKey(
        "candidate.Profile", 
        on_delete=models.CASCADE, 
        related_name="interviews"
    )

    round_name = models.CharField(max_length=150, default="Technical Interview")
    interview_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default="video")
    
    scheduled_at = models.DateTimeField(help_text="Scheduled date and time of the interview")
    duration_minutes = models.PositiveIntegerField(default=45, help_text="Duration in minutes")
    
    meeting_link = models.CharField(
        max_length=500, 
        blank=True, 
        help_text="Meeting URL (Google Meet, Zoom, MS Teams) or physical location address"
    )
    interviewer_name = models.CharField(max_length=150, blank=True, help_text="Name of the interviewer or panel")
    instructions = models.TextField(blank=True, help_text="Preparation notes, topics, or agenda for the candidate")
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="scheduled")
    candidate_notes = models.TextField(blank=True, null=True, help_text="Notes/reason provided by candidate on RSVP or reschedule")
    cancellation_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_at"]

    def __str__(self):
        return f"{self.round_name} for {self.candidate} at {self.company.company_name} ({self.get_status_display()})"

    @property
    def end_time(self):
        import datetime
        return self.scheduled_at + datetime.timedelta(minutes=self.duration_minutes)

    @property
    def is_upcoming(self):
        return self.scheduled_at >= timezone.now() and self.status in ["scheduled", "confirmed", "reschedule_requested"]

    @property
    def google_calendar_url(self):
        import urllib.parse
        start_utc = self.scheduled_at.astimezone(timezone.utc)
        end_utc = self.end_time.astimezone(timezone.utc)
        start_str = start_utc.strftime("%Y%m%dT%H%M%SZ")
        end_str = end_utc.strftime("%Y%m%dT%H%M%SZ")
        title = f"Interview: {self.round_name} - {self.company.company_name}"
        details = (
            f"Position: {self.application.target_title}\n"
            f"Company: {self.company.company_name}\n"
            f"Interviewer: {self.interviewer_name or 'Hiring Team'}\n"
            f"Meeting Link / Location: {self.meeting_link or 'Online'}\n\n"
            f"Instructions:\n{self.instructions}"
        )
        location = self.meeting_link or "Online"
        params = {
            "action": "TEMPLATE",
            "text": title,
            "dates": f"{start_str}/{end_str}",
            "details": details,
            "location": location,
        }
        return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)

    def generate_ics(self):
        import datetime
        start_utc = self.scheduled_at.astimezone(timezone.utc)
        end_utc = self.end_time.astimezone(timezone.utc)
        start_str = start_utc.strftime("%Y%m%dT%H%M%SZ")
        end_str = end_utc.strftime("%Y%m%dT%H%M%SZ")
        now_str = datetime.datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        summary = f"Interview: {self.round_name} at {self.company.company_name}"
        description = (
            f"Position: {self.application.target_title}\\n"
            f"Interviewer: {self.interviewer_name or 'Hiring Team'}\\n"
            f"Meeting Link: {self.meeting_link or 'Online'}\\n\\n"
            f"Notes: {self.instructions or 'No additional instructions.'}"
        ).replace("\r", "").replace("\n", "\\n")
        location = (self.meeting_link or "Online").replace(",", "\\,")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//SkillBridge//Interview Scheduling//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:REQUEST",
            "BEGIN:VEVENT",
            f"UID:skillbridge-interview-{self.id}@skillbridge.com",
            f"DTSTAMP:{now_str}",
            f"DTSTART:{start_str}",
            f"DTEND:{end_str}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            f"LOCATION:{location}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
        return "\r\n".join(lines) + "\r\n"


