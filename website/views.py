from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from company.models import InternshipPost, JobPost, CompanyProfile
from applications.models import Application
from candidate.models import Profile


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
    Supports ?sort=newest|oldest|deadline and search ?q=keyword
    """
    today = timezone.localdate()
    sort = request.GET.get("sort", "deadline")
    q = request.GET.get("q", "").strip()
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
    )

    if q:
        internships = internships.filter(
            Q(title__icontains=q) |
            Q(company__first_name__icontains=q) |
            Q(company__last_name__icontains=q) |
            Q(city__icontains=q) |
            Q(skills__name__icontains=q)
        ).distinct()

    internships = internships.order_by(ordering)

    return render(request, "internship.html", {
        "internships": internships,
        "sort": sort,
        "q": q,
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

    user_profile = None
    has_applied_intern = False
    if request.user.is_authenticated:
        prof = Profile.objects.filter(user=request.user).first()
        if prof:
            has_applied_intern = Application.objects.filter(
                candidate=prof, internship_post=internship
        ).exclude(status__in=["withdrawn", "rejected"]).exists()
    if request.GET.get('ajax') == '1':
        return render(request, "internship_detail_partial.html", {
            "internship": internship,
            "skills_names": skills_names,
            "has_applied_intern": has_applied_intern,
        })

    return render(request, "view-intern.html", {
        "internship": internship,
        "more_internships": more_internships,
        "skills_names": skills_names,
        "has_applied_intern": has_applied_intern,
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
    Supports ?sort=newest|oldest|deadline and search ?q=keyword
    """
    today = timezone.localdate()
    sort = request.GET.get("sort", "deadline")
    q = request.GET.get("q", "").strip()
    order_map = {"newest": "-created_at", "oldest": "created_at", "deadline": "application_deadline"}
    ordering = order_map.get(sort, "application_deadline")

    jobs = (
        JobPost.objects
        .filter(is_active=True, application_deadline__gte=today)
        .select_related("company")
        .prefetch_related("skills")
    )

    if q:
        jobs = jobs.filter(
            Q(title__icontains=q) |
            Q(company__first_name__icontains=q) |
            Q(company__last_name__icontains=q) |
            Q(city__icontains=q) |
            Q(skills__name__icontains=q)
        ).distinct()

    jobs = jobs.order_by(ordering)

    return render(request, "jobs.html", {
        "jobs": jobs,
        "sort": sort,
        "q": q,
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

    user_profile = None
    has_applied_job = False
    if request.user.is_authenticated:
        prof = Profile.objects.filter(user=request.user).first()
        if prof:
            has_applied_job = Application.objects.filter(
                candidate=prof, job_post=job
            ).exclude(status__in=["withdrawn", "rejected"]).exists()
    return render(request, "view-job.html", {
        "job": job,
        "skills_names": skills_names,
        "more_jobs": more_jobs,
        "has_applied_job": has_applied_job,
    })


from django.contrib.auth.decorators import login_required
from website.models import Event, EventRegistration

def events_list_view(request):
    """
    Show all active events with search and filtering.
    """
    today = timezone.now()
    q = request.GET.get('q', '').strip()
    event_type = request.GET.get('event_type', '').strip()
    location_type = request.GET.get('location_type', '').strip()
    sort = request.GET.get('sort', 'soonest')

    events = Event.objects.filter(is_active=True)

    if q:
        events = events.filter(
            Q(title__icontains=q) |
            Q(organizer__first_name__icontains=q) |
            Q(organizer__last_name__icontains=q)
        ).distinct()

    if event_type:
        events = events.filter(event_type=event_type)

    if location_type:
        events = events.filter(location_type=location_type)

    # Sort
    if sort == 'soonest':
        events = events.order_by('start_date')
    elif sort == 'latest':
        events = events.order_by('-created_at')
    elif sort == 'past':
        events = events.filter(end_date__lt=today).order_by('-start_date')

    # By default show upcoming events first
    if sort != 'past':
        events = events.filter(end_date__gte=today)

    # Event types choice list for template
    event_types = Event.EVENT_TYPE_CHOICES
    location_types = Event.LOCATION_TYPE_CHOICES

    return render(request, 'events.html', {
        'events': events,
        'q': q,
        'selected_event_type': event_type,
        'selected_location_type': location_type,
        'sort': sort,
        'event_types': event_types,
        'location_types': location_types,
    })

def event_detail_view(request, pk: int):
    """
    Show detailed information about a single event.
    """
    event = get_object_or_404(Event.objects.select_related('organizer'), pk=pk)
    
    # Registration count
    reg_count = event.registrations.count()
    
    is_registered = False
    if request.user.is_authenticated:
        is_registered = event.registrations.filter(user=request.user).exists()

    # Determine if current user can view attendee list (organizer or staff)
    can_view_attendees = False
    attendees = []
    if request.user.is_authenticated:
        # Check if user is the organizer of the event
        is_organizer = (event.organizer and event.organizer.user == request.user)
        if is_organizer or request.user.is_staff or request.user.is_superuser:
            can_view_attendees = True
            attendees = event.registrations.select_related('user').order_by('-registered_at')

    # Recommendation: show 3 other upcoming events
    more_events = Event.objects.filter(is_active=True, end_date__gte=timezone.now()).exclude(pk=event.pk)[:3]

    return render(request, 'view-event.html', {
        'event': event,
        'reg_count': reg_count,
        'is_registered': is_registered,
        'can_view_attendees': can_view_attendees,
        'attendees': attendees,
        'more_events': more_events,
    })

@login_required
def event_register_toggle(request, pk: int):
    """
    Register or unregister the current user for an event.
    Only candidates can register for events.
    """
    if getattr(request.user, "role", None) != 'candidate':
        messages.error(request, "Only candidates can register for events.")
        return redirect('website:event_detail', pk=pk)

    event = get_object_or_404(Event, pk=pk, is_active=True)
    
    if event.end_date < timezone.now():
        messages.error(request, "This event has already ended.")
        return redirect('website:event_detail', pk=pk)

    registration = EventRegistration.objects.filter(event=event, user=request.user)
    
    if registration.exists():
        registration.delete()
        messages.success(request, f"You have successfully cancelled your registration for '{event.title}'.")
    else:
        # Create new registration
        EventRegistration.objects.create(event=event, user=request.user)
        messages.success(request, f"You are now registered for '{event.title}'!")

    return redirect('website:event_detail', pk=pk)