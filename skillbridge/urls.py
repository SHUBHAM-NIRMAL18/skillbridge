from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.sitemaps.views import sitemap
from website.sitemaps import (
    StaticViewSitemap,
    JobPostSitemap,
    InternshipPostSitemap,
    CompanySitemap,
    BlogPostSitemap,
    EventSitemap,
)

sitemaps = {
    'static': StaticViewSitemap,
    'jobs': JobPostSitemap,
    'internships': InternshipPostSitemap,
    'companies': CompanySitemap,
    'blogs': BlogPostSitemap,
    'events': EventSitemap,
}

def robots_txt(request):
    sitemap_url = request.build_absolute_uri('/sitemap.xml')
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /candidate/",
        "Disallow: /company/",
        "Disallow: /applications/",
        "Disallow: /accounts/",
        "Disallow: /communications/",
        "Disallow: /blogs/create/",
        "Disallow: /blogs/my-blogs/",
        "Allow: /",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

def custom_logout_view(request):
    """Custom logout view that redirects based on user type"""
    is_superuser = request.user.is_superuser if request.user.is_authenticated else False
    logout(request)
    
    if is_superuser:
        return redirect('/admin/login/')
    else:
        return redirect('index')

urlpatterns = [
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("admin/logout/", custom_logout_view, name='admin_logout'),
    path("admin/", admin.site.urls),
    path("company/", include("company.urls", namespace="company")),
    path('company/membership/', include(('membership.urls', 'membership'), namespace='membership')),
    path("candidate/", include("candidate.urls", namespace="candidate")),
    path("accounts/", include("allauth.urls")),
    path("", include("accounts.urls")),
    path("", include(("website.urls", "website"), namespace="website")),
    path("applications/", include(("applications.urls", "applications"), namespace="applications")),
    path("communications/", include(("communications.urls", "communications"), namespace="communications")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)