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
from django.utils import timezone
from django.db.models.functions import Coalesce
from django.db.models import Sum

from .forms import (
    CompanyProfileForm, BasicDetailsForm, SkillsRequirementsForm, ReviewForm,
    InternshipPostForm, JobBasicDetailsForm, JobSkillsRequirementsForm, JobReviewForm,
    JobPostForm, CustomPasswordChangeForm, NotificationSettingsForm
)
from .forms_onboarding import CompanyOnboardingForm
from .models import CompanyProfile, InternshipPost, JobPost
from applications.models import Application
from candidate.models import Profile, Feedback
from communications.models import Conversation, Message
from communications.services import notify_user

# Membership wallet helpers
from membership.services import spend_credits, get_spendable_balance


# ---------------------------
# Guards / Mixins
# ---------------------------

class RequireCompanyProfileMixin(LoginRequiredMixin):
    """
    Ensures the user is a company and has completed onboarding / CompanyProfile row.
    Redirects to the Company Onboarding page with a message if missing.
    """
    def dispatch(self, request, *args, **kwargs):
        # must be a company user
        if getattr(request.user, "role", None) != getattr(request.user, "ROLE_COMPANY", "company"):
            messages.error(request, "Please sign in with a company account.")
            return redirect("accounts:login")

        # must have completed company profile & onboarding
        if not getattr(request.user, "has_completed_onboarding", False) or not hasattr(request.user, "company_profile"):
            messages.info(request, "Please complete your company onboarding before accessing this page.")
            return redirect("company:onboarding")

        return super().dispatch(request, *args, **kwargs)


# ---------------------------
# Company Onboarding Flow
# ---------------------------

@login_required
def company_onboarding(request):
    if getattr(request.user, "role", None) != getattr(request.user, "ROLE_COMPANY", "company"):
        messages.error(request, "Please switch to a company account.")
        if getattr(request.user, "role", None) == getattr(request.user, "ROLE_CANDIDATE", "candidate"):
            return redirect("candidate:onboarding")
        return redirect("accounts:login")

    try:
        profile = request.user.company_profile
    except CompanyProfile.DoesNotExist:
        profile = CompanyProfile(user=request.user)

    show_complete = request.GET.get('step') == 'complete' or (
        request.user.has_completed_onboarding and request.GET.get('edit') != '1'
    )

    if request.method == "POST":
        form = CompanyOnboardingForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            p = form.save(commit=False)
            p.user = request.user
            p.is_active = True
            if not p.pk and not p.credits_balance:
                p.credits_balance = getattr(settings, 'CREDITS_SIGNUP_BONUS', 50)
            p.save()

            request.user.is_onboarded = True
            request.user.save(update_fields=['is_onboarded'])

            messages.success(request, "🎉 Company profile setup complete! Welcome to SkillBridge.")
            return redirect(f"{reverse('company:onboarding')}?step=complete")
    else:
        form = CompanyOnboardingForm(instance=profile)

    return render(request, "company/onboarding.html", {
        'form': form,
        'profile': profile,
        'show_complete': show_complete,
        'credits_balance': profile.credits_balance if profile.pk else getattr(settings, 'CREDITS_SIGNUP_BONUS', 50),
    })


# ---------------------------
# Dashboard
# ---------------------------

@login_required
def company_dashboard(request):
    # guards
    if getattr(request.user, "role", None) != getattr(request.user, "ROLE_COMPANY", "company"):
        return redirect('accounts:login')
    if not getattr(request.user, "has_completed_onboarding", False) or not hasattr(request.user, "company_profile"):
        messages.info(request, "Please complete your company onboarding before accessing the dashboard.")
        return redirect('company:onboarding')

    company = request.user.company_profile
    today = timezone.localdate()

    # profile completeness (matches your checklist in the UI)
    profile_missing = []
    if not company.logo:
        profile_missing.append("Upload Company Images")
    if not company.social_link:
        profile_missing.append("Add Social Links")
    total_checks = 2
    profile_completion_percent = int(round(((total_checks - len(profile_missing)) / max(total_checks, 1)) * 100))

    # posts
    jobs_qs = JobPost.objects.filter(company=company)
    interns_qs = InternshipPost.objects.filter(company=company)
    total_posts = jobs_qs.count() + interns_qs.count()  # used for "Total Jobs" card per your screenshot text

    # applicants
    apps_qs = (
        Application.objects
        .select_related("candidate__user", "job_post", "internship_post")
        .filter(company=company)
    )
    total_applicants = apps_qs.count()
    shortlisted = apps_qs.filter(status="shortlisted").count()

    # views (sum if fields exist; else 0)
    try:
        views_sum = (jobs_qs.aggregate(s=Coalesce(Sum("view_count"), 0))["s"] or 0) + \
                    (interns_qs.aggregate(s=Coalesce(Sum("view_count"), 0))["s"] or 0)
    except Exception:
        views_sum = 0

    metrics = {
        "total_jobs": total_posts,          # change to jobs_qs.count() if you want only job posts
        "total_applicants": total_applicants,
        "shortlisted": shortlisted,
        "views": views_sum,
    }

    # new applications (last 7 days, newest first)
    last_7 = timezone.now() - timezone.timedelta(days=7)
    new_apps = apps_qs.filter(applied_at__gte=last_7).order_by("-applied_at")

    new_applications = []
    for a in new_apps[:8]:
        posting = a.job_post or a.internship_post
        title = getattr(posting, "title", "—")
        candidate = getattr(a, "candidate", None)
        cand_name = (f"{getattr(candidate, 'first_name', '')} {getattr(candidate, 'last_name', '')}").strip() \
                    or getattr(getattr(candidate, "user", None), "username", "Candidate")
        new_applications.append({
            "id": a.id,
            "candidate_name": cand_name,
            "job_title": title,
            "created_at": a.applied_at,
        })

    # recent activities (last updates on posts)
    recent_activities = []
    for j in jobs_qs.values("title", "created_at", "updated_at").order_by("-updated_at", "-created_at")[:5]:
        recent_activities.append({"kind": "Job", "title": j["title"], "when": j["updated_at"] or j["created_at"]})
    for i in interns_qs.values("title", "created_at", "updated_at").order_by("-updated_at", "-created_at")[:5]:
        recent_activities.append({"kind": "Internship", "title": i["title"], "when": i["updated_at"] or i["created_at"]})
    recent_activities.sort(key=lambda x: x["when"], reverse=True)
    recent_activities = recent_activities[:6]

    # expiring soon (next 7 days)
    expiring_soon = list(
        jobs_qs.filter(is_active=True, application_deadline__gte=today, application_deadline__lte=today + timezone.timedelta(days=7))
               .values("id", "title", "application_deadline")
    ) + list(
        interns_qs.filter(is_active=True, application_deadline__gte=today, application_deadline__lte=today + timezone.timedelta(days=7))
                  .values("id", "title", "application_deadline")
    )

    # Scheduled upcoming interviews
    upcoming_interviews = []
    try:
        from applications.models import Interview
        upcoming_interviews = list(
            Interview.objects
            .select_related("candidate", "application__job_post", "application__internship_post")
            .filter(
                company=company,
                scheduled_at__gte=timezone.now(),
                status__in=["scheduled", "confirmed", "reschedule_requested"]
            )
            .order_by("scheduled_at")[:5]
        )
    except Exception:
        upcoming_interviews = []

    metrics["upcoming_interviews"] = len(upcoming_interviews)

    context = {
        "company": company,
        "metrics": metrics,
        "is_profile_complete": len(profile_missing) == 0,
        "profile_missing": profile_missing,
        "profile_completion_percent": profile_completion_percent,
        "new_applications": new_applications,
        "upcoming_interviews": upcoming_interviews,
        "recent_activities": recent_activities,
        "expiring_soon": expiring_soon,
    }
    return render(request, "company/dashboard.html", context)

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
          .prefetch_related("candidate__projects", "candidate__experiences", "candidate__educations")
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
    sort = request.GET.get("sort", "newest")  # newest|oldest|best_match

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

    # Counts for header badges
    counts = dict(qs.values("status").annotate(c=Count("id")).values_list("status", "c"))
    total_all = qs.count()
    total_job = qs.filter(job_post__isnull=False).count()
    total_int = qs.filter(internship_post__isnull=False).count()

    # Compute applicant candidate fit scores
    from recommendations.simple_hybrid import compute_candidate_job_fit, recommend_candidates_for_job
    app_list = list(qs)
    for a in app_list:
        target_obj = a.job_post if a.is_job else a.internship_post
        if target_obj and a.candidate:
            try:
                fit = compute_candidate_job_fit(a.candidate, target_obj)
                a.match_score = int(round(fit.score * 100))
                a.matched_skills = fit.matched_skills
                a.missing_skills = fit.missing_skills
                a.match_why = fit.why
            except Exception:
                a.match_score = 0
                a.matched_skills = []
                a.missing_skills = []
                a.match_why = ""
        else:
            a.match_score = 0
            a.matched_skills = []
            a.missing_skills = []
            a.match_why = ""

    # Sort applications
    if sort in ["best_match", "match"]:
        app_list.sort(key=lambda x: (x.match_score, x.applied_at), reverse=True)
    elif sort == "oldest":
        app_list.sort(key=lambda x: x.applied_at)
    else:  # newest
        app_list.sort(key=lambda x: x.applied_at, reverse=True)

    page_obj = Paginator(app_list, 12).get_page(request.GET.get("page"))

    # Suggested candidates (talent sourcing for specific posting)
    suggested_candidates = []
    if posting:
        try:
            already_applied_cand_ids = {a.candidate_id for a in app_list}
            raw_cand_recs = recommend_candidates_for_job(posting, limit=12)
            for r in raw_cand_recs:
                if r.obj_id not in already_applied_cand_ids:
                    cand_prof = Profile.objects.filter(id=r.obj_id).select_related("user").first()
                    if cand_prof:
                        suggested_candidates.append({
                            "profile": cand_prof,
                            "score": int(round(r.score * 100)),
                            "why": r.why,
                            "matched_skills": r.matched_skills,
                            "missing_skills": r.missing_skills,
                        })
                        if len(suggested_candidates) >= 4:
                            break
        except Exception:
            pass

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
        "suggested_candidates": suggested_candidates,
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

    # Fire notification to candidate
    try:
        candidate_user = app.candidate.user
        display_status = dict(Application.STATUS_CHOICES).get(new_status, new_status)
        notify_user(
            recipient=candidate_user,
            title="Application Status Updated",
            message=f"Your application for {app.target_title} at {company.company_name} was updated to '{display_status}'.",
            action_url=reverse("applications:my_applications"),
            sender=request.user,
            notification_type="application_status"
        )
    except Exception:
        pass

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
    interviews = app.interviews.all().order_by("-scheduled_at")
    latest_interview = interviews.first()

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
        "interviews": interviews,
        "latest_interview": latest_interview,
    }, request=request)

    return JsonResponse({"ok": True, "html": html, "title": f"{profile.first_name} {profile.last_name}".strip() or profile.user.username})


from website.models import Event, EventRegistration
from company.forms import EventForm

@login_required
def company_events_list(request):
    """
    List events organized by the current company.
    """
    if getattr(request.user, "role", None) != 'company':
        return redirect('accounts:login')
    if not hasattr(request.user, "company_profile"):
        messages.info(request, "Please complete your company profile first.")
        return redirect('company:profile')

    company = request.user.company_profile
    events = Event.objects.filter(organizer=company).order_by('-start_date')
    
    return render(request, 'company/events_list.html', {
        'events': events,
        'wallet_balance': getattr(company, 'credits_balance', 0),
    })

@login_required
def company_event_create(request):
    """
    Create a new event organized by the company.
    """
    if getattr(request.user, "role", None) != 'company':
        return redirect('accounts:login')
    if not hasattr(request.user, "company_profile"):
        messages.info(request, "Please complete your company profile first.")
        return redirect('company:profile')

    company = request.user.company_profile

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = company
            event.save()
            messages.success(request, f"Event '{event.title}' created successfully!")
            return redirect('company:events_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = EventForm()

    return render(request, 'company/event_form.html', {
        'form': form,
        'action_name': 'Create',
        'wallet_balance': getattr(company, 'credits_balance', 0),
    })

@login_required
def company_event_edit(request, pk: int):
    """
    Edit an existing event.
    """
    if getattr(request.user, "role", None) != 'company':
        return redirect('accounts:login')
    if not hasattr(request.user, "company_profile"):
        return redirect('company:profile')

    company = request.user.company_profile
    event = get_object_or_404(Event, pk=pk, organizer=company)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f"Event '{event.title}' updated successfully!")
            return redirect('company:events_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = EventForm(instance=event)
        # Form field formatting helper
        if event.start_date:
            form.fields['start_date'].initial = event.start_date.strftime('%Y-%m-%dT%H:%M')
        if event.end_date:
            form.fields['end_date'].initial = event.end_date.strftime('%Y-%m-%dT%H:%M')

    return render(request, 'company/event_form.html', {
        'form': form,
        'action_name': 'Edit',
        'event': event,
        'wallet_balance': getattr(company, 'credits_balance', 0),
    })

@login_required
def company_event_delete(request, pk: int):
    """
    Delete an event.
    """
    if getattr(request.user, "role", None) != 'company':
        return redirect('accounts:login')
    if not hasattr(request.user, "company_profile"):
        return redirect('company:profile')

    company = request.user.company_profile
    event = get_object_or_404(Event, pk=pk, organizer=company)
    
    if request.method == 'POST':
        event.delete()
        messages.success(request, f"Event '{event.title}' deleted successfully.")
        
    return redirect('company:events_list')


@login_required
def company_support(request):
    """
    Static/Mock support information guide page for companies
    """
    if getattr(request.user, "role", None) != 'company':
        return redirect('accounts:login')
    if not hasattr(request.user, "company_profile"):
        return redirect('company:profile')
    return render(request, "company/support.html")


@login_required
def company_feedback(request):
    """
    Logic-backed platform feedback form handler for companies
    """
    if getattr(request.user, "role", None) != 'company':
        return redirect('accounts:login')
    if not hasattr(request.user, "company_profile"):
        return redirect('company:profile')

    if request.method == "POST":
        rating = request.POST.get("rating")
        liked_features_list = request.POST.getlist("liked_features")
        comments = request.POST.get("comments", "").strip()

        if not rating:
            messages.error(request, "Please select a star rating.")
            return render(request, "company/feedback.html")

        # Save to database
        Feedback.objects.create(
            user=request.user,
            rating=int(rating),
            liked_features=", ".join(liked_features_list),
            comments=comments
        )
        messages.success(request, "Thank you for your feedback! It has been submitted successfully.")
        return redirect("company:feedback")

    return render(request, "company/feedback.html")


@login_required(login_url="accounts:login")
def company_inbox(request):
    """
    Recruiter messaging inbox to communicate directly with applicants.
    """
    if not _require_company_profile(request.user):
        messages.error(request, "Company account required.")
        return redirect("accounts:login")

    company = request.user.company_profile
    conversations = (
        Conversation.objects.filter(company=company)
        .select_related("candidate__user", "application")
        .prefetch_related("messages")
    )

    search_query = request.GET.get("q", "").strip()
    if search_query:
        conversations = conversations.filter(
            Q(candidate__first_name__icontains=search_query) |
            Q(candidate__last_name__icontains=search_query) |
            Q(subject__icontains=search_query)
        )

    active_chat_id = request.GET.get("chat_id")
    active_chat = None
    if active_chat_id:
        active_chat = conversations.filter(id=active_chat_id).first()
    if not active_chat:
        active_chat = conversations.first()

    # Mark unread messages in active thread as read
    if active_chat:
        active_chat.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    chat_list = []
    for c in conversations:
        latest = c.latest_message
        unread_count = c.unread_count_for_user(request.user)
        chat_list.append({
            "id": c.id,
            "candidate": c.candidate,
            "subject": c.subject,
            "last_message": latest.text if latest else "No messages yet",
            "timestamp": latest.created_at if latest else c.created_at,
            "unread": unread_count > 0,
            "unread_count": unread_count,
            "application": c.application,
        })

    return render(request, "company/inbox.html", {
        "chats": chat_list,
        "active_chat": active_chat,
        "search_query": search_query,
    })

