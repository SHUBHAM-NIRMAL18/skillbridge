from django.contrib import admin
from .models import CompanyProfile
# Register your models here.

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display  = ("first_name", "last_name", "industry", "company_size", "province", "city", "user_email")
    list_filter   = ("industry", "company_size", "province")
    search_fields = ("first_name", "last_name", "user__email", "city")

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Email"
