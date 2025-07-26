from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib.messages.views import SuccessMessageMixin

from django.contrib import messages

from django.shortcuts import redirect
from formtools.wizard.views import SessionWizardView


from .forms import CompanyProfileForm, BasicDetailsForm, SkillsRequirementsForm, ReviewForm, InternshipPostForm,JobBasicDetailsForm, JobSkillsRequirementsForm, JobReviewForm, JobPostForm
from .models import CompanyProfile, InternshipPost, JobPost

@login_required
def company_dashboard(request):
    # (Optional) Enforce role-matching:
    if request.user.role != request.user.ROLE_COMPANY:
        return redirect('accounts:login')
    return render(request, 'company/dashboard.html')

# company/views.py

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import InternshipPost, JobPost

class CompanyPostListView(LoginRequiredMixin, TemplateView):
    template_name = "company/all_jobs.html"
    
    def get_context_data(self, **kwargs):
        ctx     = super().get_context_data(**kwargs)
        company = self.request.user.company_profile

        # 1) Base querysets
        internships_qs = company.internships.all()
        jobs_qs        = company.job_posts.all()

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
            jobs_qs        = jobs_qs.filter(title__icontains=q)

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

        ctx["posts"] = posts
        return ctx


class InternshipPostUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = InternshipPost
    form_class = InternshipPostForm
    template_name = 'company/internship_edit.html'
    success_url = reverse_lazy('company:company_all_jobs')
    success_message = "Internship updated successfully."

    def get_queryset(self):
        return self.request.user.company_profile.internships.all()


class InternshipPostDeleteView(LoginRequiredMixin, DeleteView):
    model = InternshipPost
    success_url = reverse_lazy('company:company_all_jobs')

    def get_queryset(self):
        return self.request.user.company_profile.internships.all()

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Internship deleted successfully.")
        return super().delete(request, *args, **kwargs)
    
class JobPostUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model         = JobPost
    form_class    = JobPostForm
    template_name = 'company/job_edit.html'
    success_url   = reverse_lazy('company:company_all_jobs')
    success_message = "Job updated successfully."

    def get_queryset(self):
        # only allow editing your own posts
        return self.request.user.company_profile.job_posts.all()


class JobPostDeleteView(LoginRequiredMixin, DeleteView):
    model         = JobPost
    template_name = 'company/job_confirm_delete.html'
    success_url   = reverse_lazy('company:company_all_jobs')

    def get_queryset(self):
        # only allow deleting your own posts
        return self.request.user.company_profile.job_posts.all()

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Job deleted successfully.")
        return super().delete(request, *args, **kwargs)
    
class InternshipPostDetailView(LoginRequiredMixin, DetailView):
    model = InternshipPost
    template_name = 'company/internship_detail.html'
    context_object_name = 'post'
    def get_queryset(self):
        return self.request.user.company_profile.internships.all()

class JobPostDetailView(LoginRequiredMixin, DetailView):
    model = JobPost
    template_name = 'company/job_detail.html'
    context_object_name = 'post'
    def get_queryset(self):
        return self.request.user.company_profile.job_posts.all()

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


FORMS = [
    ('basic', BasicDetailsForm),
    ('skills', SkillsRequirementsForm),
    ('review', ReviewForm),
]

INTERNSHIP_TEMPLATES = {
    'basic':  'company/internship_wizard_basic.html',
    'skills': 'company/internship_wizard_skills.html',
    'review': 'company/internship_wizard_review.html',
}

class InternshipWizard(SessionWizardView):
    form_list = FORMS
    url_name = 'company:internship_step'   # ← move here
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
        context['basic_data']  = self.get_cleaned_data_for_step('basic')  or {}
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



FORMS = [
    ('basic',   JobBasicDetailsForm),
    ('details', JobSkillsRequirementsForm),
    ('review',  JobReviewForm),
]

TEMPLATES = {
    'basic':   'company/job_wizard_basic.html',
    'details': 'company/job_wizard_details.html',
    'review':  'company/job_wizard_review.html',
}

@method_decorator(login_required, name='dispatch')
class JobWizard(SessionWizardView):
    form_list      = FORMS
    url_name       = 'company:job_step'
    done_step_name = 'review'
    template_name  = None

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def get_context_data(self, form, **kwargs):
        ctx = super().get_context_data(form=form, **kwargs)
        ctx['basic_data']   = self.get_cleaned_data_for_step('basic')   or {}
        ctx['details_data'] = self.get_cleaned_data_for_step('details') or {}
        return ctx

    def done(self, form_list, **kwargs):
        data = {}
        for f in form_list:
            data.update(f.cleaned_data)

        job = JobPost.objects.create(
            company              = self.request.user.company_profile,
            title                = data['title'],
            province             = data['province'],
            city                 = data['city'],
            location_type        = data['location_type'],
            sector               = data['sector'],
            application_deadline = data['application_deadline'],
            job_type             = data['job_type'],
            job_level            = data['job_level'],
            experience_required  = data['experience_required'],
            experience_unit      = data['experience_unit'],
            openings             = data['openings'],
            salary_min           = data['salary_min'],
            salary_max           = data['salary_max'],
            salary_period        = data['salary_period'],
            responsibilities     = data['responsibilities'],
            qualifications       = data['qualifications'],
            benefits             = data['benefits'],
        )
        job.skills.set(data.get('skills', []))
        messages.success(self.request, "Job posted successfully!")
        return redirect(reverse('company:company_all_jobs'))