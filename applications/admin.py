from django.contrib import admin
from .models import Application

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "company", "target", "status", "applied_at")
    list_filter  = ("status", "applied_at")
    search_fields = ("candidate__user__username", "candidate__first_name", "candidate__last_name",
                     "company__first_name", "company__last_name")
    # use raw ids to avoid the system check requirement
    raw_id_fields = ("candidate", "company", "job_post", "internship_post")

    def target(self, obj):
        return obj.target_title
