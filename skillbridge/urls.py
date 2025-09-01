"""
URL configuration for skillbridge project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.urls import include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("company/", include("company.urls", namespace="company")),
    path('company/membership/', include(('membership.urls', 'membership'), namespace='membership')),
    path("candidate/", include("candidate.urls", namespace="candidate")),
    path("", include("accounts.urls")),
    path("", include(("website.urls", "website"), namespace="website")),
    path("applications/", include(("applications.urls", "applications"), namespace="applications")),
    # Add other app URLs here as needed
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
