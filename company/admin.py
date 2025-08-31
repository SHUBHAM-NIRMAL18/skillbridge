from django.contrib import admin

# Register your models here.
from .models import Sector

@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "display_order", "slug")
    list_editable = ("is_active", "display_order")
    search_fields = ("name", "slug")