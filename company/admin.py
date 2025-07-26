from django.contrib import admin
from .models import CompanyProfile, InternshipPost
# Register your models here.

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display  = ("first_name", "last_name", "industry", "company_size", "province", "city", "user_email","is_active")
    list_filter   = ("industry", "company_size", "province",)
    search_fields = ("first_name", "last_name", "user__email", "city")
    list_editable = ("is_active",)
    

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Email"

    def is_active(self, obj):
        return obj.user.is_active
    is_active.boolean = True
    is_active.short_description = 'Active?'




@admin.register(InternshipPost)
class InternshipPostAdmin(admin.ModelAdmin):
    list_display = (
        "title", "company", "city", "location", "sector",
        "application_deadline", "type", "level", "openings",
        "comp_min", "comp_max", "comp_frequency", "created_at",
    )
    list_filter = (
        "location", "sector", "type", "level",
        "comp_frequency", "application_deadline",
    )
    search_fields = (
        "title", "city",
        "company__user__email",
        "company__first_name", "company__last_name",
    )
    date_hierarchy   = "application_deadline"
    filter_horizontal = ("skills",)
    raw_id_fields     = ("company",)

    fieldsets = (
        ("Basic Details", {
            "fields": (
                "company", "title", "city", "location", "sector",
                "application_deadline", "type", "level", "openings",
                ("comp_min", "comp_max", "comp_frequency"),
            )
        }),
        ("Skills & Requirements", {
            "fields": ("skills", "responsibilities", "qualifications", "benefits")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("created_at", "updated_at")


from django.contrib import admin
from .models import JobPost

@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "province",
        "city",
        "job_type",
        "job_level",
        "is_active",
        "application_deadline",
        "status",
    )
    list_filter = (
        "company",
        "province",
        "city",
        "job_type",
        "job_level",
        "is_active",
    )
    search_fields = (
        "title",
        "company__user__email",
        "company__first_name",
        "company__last_name",
    )
    date_hierarchy = "application_deadline"
    ordering = ("-created_at",)
    raw_id_fields = ("company",)
    filter_horizontal = ("skills",)

    def get_skills(self, obj):
        return ", ".join(tag.name for tag in obj.skills.all())
    get_skills.short_description = "Skills"

    # Add the skills column to the display
    list_display = list_display + ("get_skills",)

