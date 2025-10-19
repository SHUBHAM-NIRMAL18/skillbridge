from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import HttpResponseRedirect

def custom_logout_view(request):
    """Custom logout view that redirects based on user type"""
    is_superuser = request.user.is_superuser if request.user.is_authenticated else False
    logout(request)
    
    if is_superuser:
        return redirect('/admin/login/')
    else:
        return redirect('index')

urlpatterns = [
    path("admin/logout/", custom_logout_view, name='admin_logout'),
    path("admin/", admin.site.urls),
    path("company/", include("company.urls", namespace="company")),
    path('company/membership/', include(('membership.urls', 'membership'), namespace='membership')),
    path("candidate/", include("candidate.urls", namespace="candidate")),
    path("accounts/", include("allauth.urls")),
    path("", include("accounts.urls")),
    path("", include(("website.urls", "website"), namespace="website")),
    path("applications/", include(("applications.urls", "applications"), namespace="applications")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)