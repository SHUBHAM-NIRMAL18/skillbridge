from django.contrib import admin
from website.models import Event, EventRegistration, BlogPost

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'location_type', 'start_date', 'organizer', 'is_active')
    list_filter = ('event_type', 'location_type', 'is_active', 'start_date')
    search_fields = ('title', 'organizer__first_name', 'organizer__last_name')
    date_hierarchy = 'start_date'

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'registered_at')
    list_filter = ('event', 'registered_at')
    search_fields = ('user__email', 'event__title')


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_verified', 'created_at', 'updated_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('title', 'author__email', 'content')
    list_editable = ('is_verified',)
    prepopulated_fields = {'slug': ('title',)}


