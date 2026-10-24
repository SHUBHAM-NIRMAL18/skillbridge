from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from company.models import JobPost, InternshipPost, CompanyProfile
from website.models import BlogPost, Event


class StaticViewSitemap(Sitemap):
    """Sitemap for key static and listing pages."""
    protocol = 'https'

    priority_map = {
        'website:index': 1.0,
        'website:jobs_list': 0.9,
        'website:internship': 0.9,
        'website:events_list': 0.8,
        'website:blog_list': 0.8,
        'website:privacy': 0.3,
        'website:terms': 0.3,
    }

    changefreq_map = {
        'website:index': 'daily',
        'website:jobs_list': 'daily',
        'website:internship': 'daily',
        'website:events_list': 'daily',
        'website:blog_list': 'daily',
        'website:privacy': 'monthly',
        'website:terms': 'monthly',
    }

    def items(self):
        return [
            'website:index',
            'website:jobs_list',
            'website:internship',
            'website:events_list',
            'website:blog_list',
            'website:privacy',
            'website:terms',
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self.priority_map.get(item, 0.5)

    def changefreq(self, item):
        return self.changefreq_map.get(item, 'weekly')


class JobPostSitemap(Sitemap):
    """Sitemap for active job listings."""
    changefreq = 'weekly'
    priority = 0.9
    protocol = 'https'

    def items(self):
        return (
            JobPost.objects
            .filter(is_active=True, application_deadline__gte=timezone.localdate())
            .select_related('company')
            .order_by('-created_at')
        )

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        if obj.slug:
            return reverse('website:job_detail', kwargs={'slug': obj.slug})
        return reverse('website:job_detail_by_pk', kwargs={'pk': obj.pk})


class InternshipPostSitemap(Sitemap):
    """Sitemap for active internship listings."""
    changefreq = 'weekly'
    priority = 0.85
    protocol = 'https'

    def items(self):
        return (
            InternshipPost.objects
            .filter(is_active=True, application_deadline__gte=timezone.localdate())
            .select_related('company')
            .order_by('-created_at')
        )

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('website:internship_detail', kwargs={'pk': obj.pk})


class CompanySitemap(Sitemap):
    """Sitemap for registered active company profile pages."""
    changefreq = 'weekly'
    priority = 0.75
    protocol = 'https'

    def items(self):
        return CompanyProfile.objects.filter(is_active=True).order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('website:company_detail', kwargs={'pk': obj.pk})


class BlogPostSitemap(Sitemap):
    """Sitemap for verified community blog articles."""
    changefreq = 'monthly'
    priority = 0.7
    protocol = 'https'

    def items(self):
        return BlogPost.objects.filter(is_verified=True).order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('website:blog_detail', kwargs={'slug': obj.slug})


class EventSitemap(Sitemap):
    """Sitemap for active workshops, webinars, and events."""
    changefreq = 'weekly'
    priority = 0.75
    protocol = 'https'

    def items(self):
        return Event.objects.filter(is_active=True).order_by('-start_date')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('website:event_detail', kwargs={'pk': obj.pk})
