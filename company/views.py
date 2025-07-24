from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CompanyProfileForm, BasicDetailsForm, SkillsRequirementsForm, ReviewForm
from django.contrib import messages
from .models import CompanyProfile, InternshipPost
from django.shortcuts import redirect
from formtools.wizard.views import SessionWizardView

@login_required
def company_dashboard(request):
    # (Optional) Enforce role-matching:
    if request.user.role != request.user.ROLE_COMPANY:
        return redirect('accounts:login')
    return render(request, 'company/dashboard.html')

@login_required
def alljobs_view(request):
    return render(request, 'company/all_jobs.html')

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
