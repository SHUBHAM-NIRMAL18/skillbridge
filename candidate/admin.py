from django.contrib import admin
from .models import Profile, SocialLink, Education, Experience, Project, Certificate

# Register your models here.
admin.site.register(Profile)
admin.site.register(SocialLink)
admin.site.register(Education)
admin.site.register(Experience)
admin.site.register(Project)
admin.site.register(Certificate) 