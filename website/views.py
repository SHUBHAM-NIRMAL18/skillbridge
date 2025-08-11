from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from company.models import InternshipPost, JobPost, CompanyProfile

# Create your views here.
def home_view(request):
    """
    Render the home page with the upcoming internships AND jobs.
    """
    today = timezone.localdate()

    internships = (
        InternshipPost.objects
        .filter(is_active=True, application_deadline__gte=today)
        .order_by('application_deadline')[:6]
    )

    jobs = (
        JobPost.objects
        .filter(is_active=True, application_deadline__gte=today)
        .order_by('application_deadline')[:6]
    )

    return render(request, 'index.html', {
        'internships': internships,
        'jobs':        jobs,
    })

# def login_view(request):
#     """
#     Render the login page.
#     """
#     return render(request, 'accounts/login.html')

def privacy_policy_view(request):
    """
    Render the privacy policy page.
    """
    return render(request, 'privacy.html')


def termcondition_view(request):
    """
    Render the terms and conditions page.
    """
    return render(request, 'termcondition.html')

def internships_list_view(request):
    """
    Show ALL active, non-expired internships (soonest deadline first by default).
    Supports ?sort=newest|oldest|deadline
    """
    today = timezone.localdate()
    sort = request.GET.get("sort", "deadline")
    order_map = {
        "newest": "-created_at",
        "oldest": "created_at",
        "deadline": "application_deadline",
    }
    ordering = order_map.get(sort, "application_deadline")

    internships = (
        InternshipPost.objects
        .filter(is_active=True, application_deadline__gte=today)
        .select_related("company")
        .prefetch_related("skills")
        .order_by(ordering)
    )

    return render(request, "internship.html", {
        "internships": internships,
        "sort": sort,
    })


def internship_detail_view(request, pk: int):
    """
    Full-page dynamic internship detail.
    """
    internship = get_object_or_404(
        InternshipPost.objects.select_related("company").prefetch_related("skills"),
        pk=pk
    )

    # <- NEW: make a plain list of names so the template can't trip over Taggit's manager
    skills_names = list(
        internship.skills.order_by("name").values_list("name", flat=True)
    )

    today = timezone.localdate()
    more_internships = (
        InternshipPost.objects
        .filter(
            company=internship.company,
            is_active=True,
            application_deadline__gte=today
        )
        .exclude(pk=internship.pk)
        .select_related("company")
        .order_by("application_deadline")[:3]
    )

    return render(request, "view-intern.html", {
        "internship": internship,
        "more_internships": more_internships,
        "skills_names": skills_names,   # <- pass to template
    })

def company_detail_view(request, pk: int):
    company = get_object_or_404(CompanyProfile, pk=pk)
    today = timezone.localdate()

    active_internships = (
        InternshipPost.objects
        .filter(company=company, is_active=True, application_deadline__gte=today)
        .order_by("application_deadline")
        .prefetch_related("skills")
    )
    active_jobs = (
        JobPost.objects
        .filter(company=company, is_active=True, application_deadline__gte=today)
        .order_by("application_deadline")
        .prefetch_related("skills")
    )

    return render(request, "company_detail.html", {
        "company": company,
        "active_internships": active_internships,
        "active_jobs": active_jobs,
    })


def jobs_list_view(request):
    """
    Show ALL active, non-expired jobs (soonest deadline by default).
    Supports ?sort=newest|oldest|deadline
    """
    today = timezone.localdate()
    sort = request.GET.get("sort", "deadline")
    order_map = {"newest": "-created_at", "oldest": "created_at", "deadline": "application_deadline"}
    ordering = order_map.get(sort, "application_deadline")

    jobs = (
        JobPost.objects
        .filter(is_active=True, application_deadline__gte=today)
        .select_related("company")
        .prefetch_related("skills")
        .order_by(ordering)
    )

    return render(request, "jobs.html", {
        "jobs": jobs,
        "sort": sort,
    })


def job_detail_view(request, pk: int):
    """
    Full-page dynamic job detail (ID-based).
    """
    job = get_object_or_404(
        JobPost.objects.select_related("company").prefetch_related("skills"),
        pk=pk
    )

    # Robust skills list for the template
    skills_names = list(job.skills.order_by("name").values_list("name", flat=True))

    today = timezone.localdate()
    more_jobs = (
        JobPost.objects
        .filter(company=job.company, is_active=True, application_deadline__gte=today)
        .exclude(pk=job.pk)
        .select_related("company")
        .order_by("application_deadline")[:3]
    )

    return render(request, "view-job.html", {
        "job": job,
        "skills_names": skills_names,
        "more_jobs": more_jobs,
    })