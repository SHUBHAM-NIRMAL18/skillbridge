from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin

from django.contrib import messages

from django.shortcuts import redirect
from formtools.wizard.views import SessionWizardView


from .forms import CompanyProfileForm, BasicDetailsForm, SkillsRequirementsForm, ReviewForm, InternshipPostForm
from .models import CompanyProfile, InternshipPost

@login_required
def company_dashboard(request):
    # (Optional) Enforce role-matching:
    if request.user.role != request.user.ROLE_COMPANY:
        return redirect('accounts:login')
    return render(request, 'company/dashboard.html')

class InternshipPostListView(LoginRequiredMixin, ListView):
    model = InternshipPost
    template_name = 'company/all_jobs.html'
    context_object_name = 'posts'

    def get_queryset(self):
        qs = self.request.user.company_profile.internships.filter(is_active=True)
        # 1) filter by category (internship vs job)
        t = self.request.GET.get('type_filter', '')
        if t == 'internship':
            qs = qs.filter(type='Internship')    # adjust if you have a field
        elif t == 'job':
            qs = qs.filter(type='Job')
        # 2) search by title
        q = self.request.GET.get('search', '').strip()
        if q:
            qs = qs.filter(title__icontains=q)
        # 3) sort
        s = self.request.GET.get('sort', 'deadline')
        if s == 'newest':
            qs = qs.order_by('-created_at')
        elif s == 'oldest':
            qs = qs.order_by('created_at')
        else:  # deadline
            qs = qs.order_by('application_deadline')
        return qs


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
    template_name = 'company/internship_confirm_delete.html'
    success_url = reverse_lazy('company:company_all_jobs')

    def get_queryset(self):
        return self.request.user.company_profile.internships.all()

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Internship deleted successfully.")
        return super().delete(request, *args, **kwargs)

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

TEMPLATES = {
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
        return [TEMPLATES[self.steps.current]]
    
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
