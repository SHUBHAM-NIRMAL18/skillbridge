from django.db import models
from django.conf import settings
from ckeditor.fields import RichTextField

class Event(models.Model):
    EVENT_TYPE_CHOICES = [
        ('webinar', 'Webinar'),
        ('workshop', 'Workshop'),
        ('hackathon', 'Hackathon'),
        ('job_fair', 'Job Fair'),
        ('info_session', 'Info Session'),
        ('networking', 'Networking Event'),
    ]

    LOCATION_TYPE_CHOICES = [
        ('online', 'Online / Virtual'),
        ('in_person', 'In-Person'),
    ]

    title = models.CharField(max_length=255)
    description = RichTextField()
    cover_image = models.ImageField(upload_to='event_covers/', blank=True, null=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='webinar')
    location_type = models.CharField(max_length=15, choices=LOCATION_TYPE_CHOICES, default='online')
    location = models.CharField(max_length=255, help_text="Provide meeting link if online, or physical address if in-person.")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    organizer = models.ForeignKey('company.CompanyProfile', on_delete=models.CASCADE, related_name='events', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return self.title

class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_registrations')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['event', 'user'], name='unique_event_registration')
        ]
        ordering = ['-registered_at']

    def __str__(self):
        return f"{self.user.email} -> {self.event.title}"
