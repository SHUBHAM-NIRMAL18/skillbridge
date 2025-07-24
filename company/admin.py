from django.contrib import admin
from .models import CompanyProfile, InternshipPost
# Register your models here.

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display  = ("first_name", "last_name", "industry", "company_size", "province", "city", "user_email")
    list_filter   = ("industry", "company_size", "province")
    search_fields = ("first_name", "last_name", "user__email", "city")

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Email"




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
