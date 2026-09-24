from django.contrib import admin
from .models import Application, OfferLetter, Interview

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "company", "target", "status", "applied_at")
    list_filter  = ("status", "applied_at")
    search_fields = ("candidate__user__username", "candidate__first_name", "candidate__last_name",
                     "company__first_name", "company__last_name")
    raw_id_fields = ("candidate", "company", "job_post", "internship_post")

    def target(self, obj):
        return obj.target_title


@admin.register(OfferLetter)
class OfferLetterAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "company", "job_title", "status", "joining_date", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("candidate__first_name", "candidate__last_name", "company__first_name", "job_title")
    raw_id_fields = ("application", "company", "candidate")


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ("id", "round_name", "candidate", "company", "scheduled_at", "duration_minutes", "interview_type", "status")
    list_filter = ("status", "interview_type", "scheduled_at")
    search_fields = ("candidate__first_name", "candidate__last_name", "company__first_name", "round_name")
    raw_id_fields = ("application", "company", "candidate")

