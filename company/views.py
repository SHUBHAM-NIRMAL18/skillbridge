from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, logout
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import PasswordChangeForm
from django.views.generic import UpdateView, DeleteView, DetailView, TemplateView
from django.urls import reverse_lazy, reverse
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from formtools.wizard.views import SessionWizardView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, F
from django.http import HttpResponseForbidden, JsonResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction

from .forms import (
    CompanyProfileForm, BasicDetailsForm, SkillsRequirementsForm, ReviewForm,
    InternshipPostForm, JobBasicDetailsForm, JobSkillsRequirementsForm, JobReviewForm,
    JobPostForm, CustomPasswordChangeForm, NotificationSettingsForm
)
from .models import CompanyProfile, InternshipPost, JobPost
from applications.models import Application
from candidate.models import Profile

# Membership wallet helpers
from membership.services import spend_credits, get_spendable_balance


# ---------------------------
# Guards / Mixins
# ---------------------------

class RequireCompanyProfileMixin(LoginRequiredMixin):
    """
    Ensures the user is a company and has a CompanyProfile row.
    Redirects to the Company Profile page with a message if missing.
    """
    def dispatch(self, request, *args, **kwargs):
        # must be a company user
        if getattr(request.user, "role", None) != getattr(request.user, "ROLE_COMPANY", "company"):
            messages.error(request, "Please sign in with a company account.")
            return redirect("accounts:login")

        # must have completed company profile
        if not hasattr(request.user, "company_profile"):
            messages.info(request, "Please complete your company profile before accessing this page.")
            return redirect("company:profile")

        return super().dispatch(request, *args, **kwargs)


# ---------------------------
# Dashboard
# ---------------------------

@login_required
def company_dashboard(request):
    if getattr(request.user, "role", None) != getattr(request.user, "ROLE_COMPANY", "company"):
        return redirect('accounts:login')
    if not hasattr(request.user, "company_profile"):
        messages.info(request, "Please complete your company profile before accessing the dashboard.")
        return redirect('company:profile')
    return render(request, 'company/dashboard.html')


# ---------------------------
# Company Posts List
# ---------------------------

class CompanyPostListView(RequireCompanyProfileMixin, TemplateView):
    template_name = "company/all_jobs.html"
    paginate_by = 10  # Number of posts per page

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = self.request.user.company_profile

        # 1) Base querysets
        internships_qs = company.internships.all()
        jobs_qs = company.job_posts.all()

        # 2) Type filter
        t = self.request.GET.get("type_filter", "")
        if t == "internship":
            jobs_qs = jobs_qs.none()
        elif t == "job":
            internships_qs = internships_qs.none()

        # 3) Search filter
        q = self.request.GET.get("search", "").strip()
        if q:
            internships_qs = internships_qs.filter(title__icontains=q)
            jobs_qs = jobs_qs.filter(title__icontains=q)

        # 4) Convert to lists & tag each
        internships = list(internships_qs)
        for inst in internships:
            inst.post_type = "internship"

        jobs = list(jobs_qs)
        for job in jobs:
            job.post_type = "job"

        # 5) Merge and sort
        posts = internships + jobs
        sort = self.request.GET.get("sort", "deadline")
        if sort == "newest":
            posts.sort(key=lambda p: p.created_at, reverse=True)
        elif sort == "oldest":
            posts.sort(key=lambda p: p.created_at)
        else:  # deadline
            posts.sort(key=lambda p: p.application_deadline)

        # 6) Pagination
        paginator = Paginator(posts, self.paginate_by)
        page_number = self.request.GET.get('page')

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page
            page_obj = paginator.page(1)
        except EmptyPage:
            # If page is out of range, deliver last page
            page_obj = paginator.page(paginator.num_pages)

        ctx["posts"] = page_obj.object_list
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["is_paginated"] = page_obj.has_other_pages()

        return ctx


# ---------------------------
# Internship: Update / Delete / Detail
# ---------------------------

class InternshipPostUpdateView(RequireCompanyProfileMixin, SuccessMessageMixin, UpdateView):
    model = InternshipPost
    form_class = InternshipPostForm
    template_name = 'company/internship_edit.html'
    success_url = reverse_lazy('company:company_all_jobs')
    success_message = "Internship updated successfully."

    def get_queryset(self):
        return self.request.user.company_profile.internships.all()


class InternshipPostDeleteView(RequireCompanyProfileMixin, DeleteView):
    model = InternshipPost
    success_url = reverse_lazy('company:company_all_jobs')

    def get_queryset(self):
        return self.request.user.company_profile.internships.all()

    # Ensure message for both POST and DELETE
    def post(self, request, *args, **kwargs):
        messages.success(request, "Internship deleted successfully.")
        return super().delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Internship deleted successfully.")
        return super().delete(request, *args, **kwargs)


class InternshipPostDetailView(RequireCompanyProfileMixin, DetailView):
    model = InternshipPost
    template_name = 'company/internship_detail.html'
    context_object_name = 'post'

    def get_queryset(self):
        return self.request.user.company_profile.internships.all()


# ---------------------------
# Job: Update / Delete / Detail
# ---------------------------

class JobPostUpdateView(RequireCompanyProfileMixin, SuccessMessageMixin, UpdateView):
    model = JobPost
    form_class = JobPostForm
    template_name = 'company/job_edit.html'
    success_url = reverse_lazy('company:company_all_jobs')
    success_message = "Job updated successfully."

    def get_queryset(self):
        # only allow editing your own posts
        return self.request.user.company_profile.job_posts.all()


class JobPostDeleteView(RequireCompanyProfileMixin, DeleteView):
    model = JobPost
    template_name = 'company/job_confirm_delete.html'
    success_url = reverse_lazy('company:company_all_jobs')

    def get_queryset(self):
        # only allow deleting your own posts
        return self.request.user.company_profile.job_posts.all()

    # Ensure message for both POST and DELETE
    def post(self, request, *args, **kwargs):
        messages.success(request, "Job deleted successfully.")
        return super().delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Job deleted successfully.")
        return super().delete(request, *args, **kwargs)


class JobPostDetailView(RequireCompanyProfileMixin, DetailView):
    model = JobPost
    template_name = 'company/job_detail.html'
    context_object_name = 'post'

    def get_queryset(self):
        return self.request.user.company_profile.job_posts.all()


# ---------------------------
# Misc Company pages
# ---------------------------

@login_required
def post_choice_view(request):
    return render(request, 'company/post_choice.html')


@login_required
def company_profile(request):
    # try to fetch an existing profile; if none, just prepare an unsaved instance
    try:
        profile = request.user.company_profile
    except CompanyProfile.DoesNotExist:
        profile = CompanyProfile(user=request.user)

    if request.method == 'POST':
        form = CompanyProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # form.save(commit=False) so we can ensure user is set
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, "Your company profile was updated.")
            return redirect('company:profile')
    else:
        form = CompanyProfileForm(instance=profile)

    return render(request, 'company/company_profile.html', {
        'form': form,
        'profile': profile
    })


# ---------------------------
# Internship Wizard
# ---------------------------

FORMS = [
    ('basic', BasicDetailsForm),
    ('skills', SkillsRequirementsForm),
    ('review', ReviewForm),
]

INTERNSHIP_TEMPLATES = {
    'basic': 'company/internship_wizard_basic.html',
    'skills': 'company/internship_wizard_skills.html',
    'review': 'company/internship_wizard_review.html',
}

class InternshipWizard(SessionWizardView):
    form_list = FORMS
    url_name = 'company:internship_step'
    done_step_name = 'review'
    template_name = None

    def get_template_names(self):
        return [INTERNSHIP_TEMPLATES[self.steps.current]]

    def get_context_data(self, form, **kwargs):
        """
        Inject the cleaned_data for steps 'basic' & 'skills'
        so templates can just use {{ basic_data }} & {{ skills_data }}.
        """
        context = super().get_context_data(form=form, **kwargs)
        context['basic_data'] = self.get_cleaned_data_for_step('basic') or {}
        context['skills_data'] = self.get_cleaned_data_for_step('skills') or {}
        return context

    def done(self, form_list, **kwargs):
        data = self.get_all_cleaned_data()
        post = InternshipPost.objects.create(
            company=self.request.user.company_profile,
            title=data['title'],
            city=data['city'],
            location=data['location'],
            sector=data['sector'],
            application_deadline=data['application_deadline'],
            type=data['type'],
            level=data['level'],
            openings=data['openings'],
            comp_min=data['comp_min'],
            comp_max=data['comp_max'],
            comp_frequency=data['comp_frequency'],
            responsibilities=data['responsibilities'],
            qualifications=data['qualifications'],
            benefits=data['benefits'],
        )
        post.skills.set(data.get('skills', []))
        messages.success(self.request, "Internship posted successfully!")
        return redirect('company:company_all_jobs')


# ---------------------------
# Job Wizard (charges credits)
# ---------------------------

FORMS = [
    ('basic', JobBasicDetailsForm),
    ('details', JobSkillsRequirementsForm),
    ('review', JobReviewForm),
]

TEMPLATES = {
    'basic': 'company/job_wizard_basic.html',
    'details': 'company/job_wizard_details.html',
    'review': 'company/job_wizard_review.html',
}

@method_decorator(login_required, name='dispatch')
class JobWizard(RequireCompanyProfileMixin, SessionWizardView):
    form_list = FORMS
    url_name = 'company:job_step'
    done_step_name = 'review'
    template_name = None

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def get_context_data(self, form, **kwargs):
        ctx = super().get_context_data(form=form, **kwargs)
        ctx['basic_data'] = self.get_cleaned_data_for_step('basic') or {}
        ctx['details_data'] = self.get_cleaned_data_for_step('details') or {}
        return ctx

    def done(self, form_list, **kwargs):
        # 1) collect wizard data
        data = {}
        for f in form_list:
            data.update(f.cleaned_data)

        company = self.request.user.company_profile
        cost = getattr(settings, "CREDITS_JOB_POST", 10)

        try:
            with transaction.atomic():
                # 2) charge credits first (atomic; uses wallet/ledger/batches)
                #    NOTE: raises ValueError("INSUFFICIENT_CREDITS:...") if not enough
                spend_credits(
                    company,
                    amount=cost,
                    reason="JOB_POST_CREATE",
                    meta={"flow": "wizard"}
                )

                # 3) create the job (posted immediately)
                job = JobPost.objects.create(
                    company=company,
                    title=data['title'],
                    province=data['province'],
                    city=data['city'],
                    location_type=data['location_type'],
                    sector=data['sector'],
                    application_deadline=data['application_deadline'],
                    job_type=data['job_type'],
                    job_level=data['job_level'],
                    experience_required=data['experience_required'],
                    experience_unit=data['experience_unit'],
                    openings=data['openings'],
                    salary_min=data['salary_min'],
                    salary_max=data['salary_max'],
                    salary_period=data['salary_period'],
                    responsibilities=data['responsibilities'],
                    qualifications=data['qualifications'],
                    benefits=data['benefits'],
                )
                job.skills.set(data.get('skills', []))

            # 4) success banner with fresh balance from wallet
            remaining = get_spendable_balance(company)
            messages.success(
                self.request,
                f"Job posted successfully. {cost} credits used. Remaining balance: {remaining}."
            )
            return redirect(reverse('company:company_all_jobs'))

        except ValueError as e:
            # Insufficient credits: spend_credits raises ValueError starting with "INSUFFICIENT_CREDITS"
            if str(e).startswith("INSUFFICIENT_CREDITS"):
                available = get_spendable_balance(company)
                messages.error(
                    self.request,
                    f"Not enough credits to post a job. You need {cost} credits, you have {available}."
                )
                # nudge to buy credits
                return redirect(reverse('membership:select'))

            # Any other issue
            messages.error(self.request, "Could not post the job right now. Please try again.")
            return redirect(reverse('company:company_all_jobs'))


# ---------------------------
# Settings / Account
# ---------------------------

@login_required
def company_settings(request):
    pw_form = CustomPasswordChangeForm(request.user, data=request.POST or None)
    notif_form = NotificationSettingsForm(
        request.POST or None,
        instance=getattr(request.user, "company_profile", None)
    )

    if request.method == 'POST':
        if 'password_submit' in request.POST and pw_form.is_valid():
            user = pw_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been updated.")
            return redirect('company:company_settings')

        if 'notify_submit' in request.POST and notif_form and notif_form.is_valid():
            notif_form.save()
            messages.success(request, "Notification settings updated.")
            return redirect('company:company_settings')

    return render(request, 'company/settings.html', {
        'pw_form': pw_form,
        'notif_form': notif_form,
    })


@require_POST
@login_required
def deactivate_account(request):
    user = request.user
    user.is_active = False
    user.save()
    logout(request)
    messages.success(request, "Your account has been deactivated.")
    return redirect('index')


# ---------------------------
# Applicants (lists / ajax updates / detail partial)
# ---------------------------

def _require_company_profile(user):
    return hasattr(user, "company_profile") and user.company_profile is not None


@login_required(login_url="accounts:login")
def applicants_list(request, pk=None, status=None):
    """
    Company-wide applicants list, with optional:
      - status filter via URL kwarg (e.g., 'applied', 'shortlisted')
      - per-posting list via pk + path (jobs/<pk>/applicants or internships/<pk>/applicants)
    Query params:
      - type = all|job|intern
      - q = search (candidate name/title)
      - sort = newest|oldest
    """
    if not _require_company_profile(request.user):
        return HttpResponseForbidden("Company account required.")

    company = request.user.company_profile

    qs = (Application.objects
          .select_related("candidate__user", "company", "job_post", "internship_post")
          .filter(company=company))

    # Per-posting filters based on the path
    if request.resolver_match.url_name == "job_applicants" and pk:
        qs = qs.filter(job_post_id=pk)
        posting = get_object_or_404(JobPost, pk=pk, company=company)
        posting_title = posting.title
        posting_type = "job"
    elif request.resolver_match.url_name == "intern_applicants" and pk:
        qs = qs.filter(internship_post_id=pk)
        posting = get_object_or_404(InternshipPost, pk=pk, company=company)
        posting_title = posting.title
        posting_type = "intern"
    else:
        posting = None
        posting_title = None
        posting_type = None

    # Sidebar pages (status via url kwarg)
    if status:
        qs = qs.filter(status=status)

    # Querystring filters
    typ = request.GET.get("type", "all")      # all|job|intern
    q = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "newest")  # newest|oldest

    if typ == "job":
        qs = qs.filter(job_post__isnull=False)
    elif typ == "intern":
        qs = qs.filter(internship_post__isnull=False)

    if q:
        qs = qs.filter(
            Q(candidate__first_name__icontains=q) |
            Q(candidate__last_name__icontains=q) |
            Q(candidate__user__username__icontains=q) |
            Q(job_post__title__icontains=q) |
            Q(internship_post__title__icontains=q)
        )

    qs = qs.order_by("-applied_at" if sort == "newest" else "applied_at")

    # Counts for header badges
    counts = dict(qs.values("status").annotate(c=Count("id")).values_list("status", "c"))
    total_all = qs.count()
    total_job = qs.filter(job_post__isnull=False).count()
    total_int = qs.filter(internship_post__isnull=False).count()

    page_obj = Paginator(qs, 12).get_page(request.GET.get("page"))

    # Status choices for dropdown
    statuses = Application.STATUS_CHOICES

    return render(request, "company/applicants_list.html", {
        "page_obj": page_obj,
        "apps": page_obj.object_list,
        "statuses": statuses,

        "counts": counts,
        "total_all": total_all,
        "total_job": total_job,
        "total_int": total_int,

        "typ": typ, "q": q, "sort": sort,
        "url_status": status,                # for tab highlight
        "posting": posting,
        "posting_title": posting_title,
        "posting_type": posting_type,
    })


@login_required(login_url="accounts:login")
def applicant_update_status(request, pk):
    """
    AJAX: update an Application.status belonging to this company.
    POST: {status: 'under_review'|'shortlisted'|'interview'|'offered'|'rejected'|'withdrawn'|'applied'}
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Invalid method."}, status=405)

    if not _require_company_profile(request.user):
        return JsonResponse({"ok": False, "error": "Company account required."}, status=403)

    company = request.user.company_profile
    app = get_object_or_404(Application.objects.select_related("company"), pk=pk, company=company)

    new_status = request.POST.get("status")
    valid_keys = {k for k, _ in Application.STATUS_CHOICES}
    if new_status not in valid_keys:
        return JsonResponse({"ok": False, "error": "Invalid status."}, status=400)

    app.status = new_status
    app.save(update_fields=["status", "updated_at"])

    # Return the new badge HTML so the row can update without reload
    label = dict(Application.STATUS_CHOICES)[new_status]
    badge_html = (
        f'<span class="badge '
        f'{"bg-secondary" if new_status=="applied" else ""}'
        f'{" bg-info text-dark" if new_status=="under_review" else ""}'
        f'{" bg-success" if new_status=="shortlisted" else ""}'
        f'{" bg-primary" if new_status in ["interview","offered"] else ""}'
        f'{" bg-danger" if new_status=="rejected" else ""}'
        f'{" bg-dark" if new_status=="withdrawn" else ""}'
        f'{" bg-light text-dark border" if new_status not in ["applied","under_review","shortlisted","interview","offered","rejected","withdrawn"] else ""}">'
        f'{label}</span>'
    )

    return JsonResponse({"ok": True, "badge": badge_html, "status": new_status})


@login_required(login_url="accounts:login")
def applicant_detail_partial(request, pk: int):
    """
    Returns the HTML partial for the right-side applicant drawer (offcanvas).
    Includes: candidate snapshot, fit summary, resume preview, cover letter, mini timeline.
    """
    if not hasattr(request.user, "company_profile"):
        return JsonResponse({"ok": False, "error": "Company account required."}, status=403)

    company = request.user.company_profile

    app = get_object_or_404(
        Application.objects.select_related(
            "candidate__user", "company", "job_post", "internship_post"
        ),
        pk=pk, company=company
    )
    profile: Profile = app.candidate

    # Posting & required skills
    posting = app.job_post if app.job_post_id else app.internship_post
    posting_type = "job" if app.job_post_id else "internship"
    required_skills = []
    if posting:
        try:
            required_skills = list(posting.skills.order_by("name").values_list("name", flat=True))
        except Exception:
            required_skills = []

    # Candidate skills (Profile.skills_list already tokenizes Tagify, CSV etc.)
    cand_skills = profile.skills_list

    # Compute overlap/missing (case-insensitive compare, display original case)
    req_lower = {s.lower(): s for s in required_skills}
    cand_lower = {s.lower(): s for s in cand_skills}
    overlap_keys = set(req_lower.keys()) & set(cand_lower.keys())
    overlap_skills = [req_lower[k] for k in sorted(overlap_keys)]
    missing_skills = [req_lower[k] for k in sorted(set(req_lower.keys()) - set(cand_lower.keys()))]

    # Status choices for drawer dropdown
    statuses = Application.STATUS_CHOICES

    html = render_to_string("company/_applicant_detail.html", {
        "app": app,
        "profile": profile,
        "posting": posting,
        "posting_type": posting_type,
        "required_skills": required_skills,
        "cand_skills": cand_skills,
        "overlap_skills": overlap_skills,
        "missing_skills": missing_skills,
        "statuses": statuses,
    }, request=request)

    return JsonResponse({"ok": True, "html": html, "title": f"{profile.first_name} {profile.last_name}".strip() or profile.user.username})
