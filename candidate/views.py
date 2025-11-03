from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView
from accounts.models import User

from .forms import (
    PersonalInfoForm, ProfessionalInfoForm, AddressInfoForm,
    EducationFormSet, ExperienceFormSet, ProjectFormSet,
    CertificateFormSet, SocialLinkFormSet, DocumentUploadForm
)
from .models import Profile
from django.utils import timezone





@login_required
def candidate_dashboard(request):
    # helpful while debugging – remove when done
    # print("AUTH:", request.user.is_authenticated, "ID:", request.user.id, "ROLE:", getattr(request.user, "role", None))

    if getattr(request.user, "role", None) != User.ROLE_CANDIDATE:
        messages.error(request, "Please use a candidate account.")
        return redirect("company:dashboard")   
    return render(request, "candidate/dashboard.html")


class ProfileWizardView(FormView):
    template_name = 'candidate/profile_wizard.html'

    # Steps that use inline formsets
    FORMSET_STEPS = ['education', 'experience', 'projects', 'certificates', 'social']

    # Order matters
    STEPS_ORDER = [
        'personal', 'professional', 'address',
        'education', 'experience', 'projects',
        'certificates', 'social', 'documents'
    ]

    # Map step -> form or formset factory
    form_classes = {
        'personal': PersonalInfoForm,
        'professional': ProfessionalInfoForm,
        'address': AddressInfoForm,
        'education': EducationFormSet,
        'experience': ExperienceFormSet,
        'projects': ProjectFormSet,
        'certificates': CertificateFormSet,
        'social': SocialLinkFormSet,
        'documents': DocumentUploadForm,
    }

    # Stable prefixes for formsets
    FORMSET_PREFIX = {
        'education': 'education',
        'experience': 'experience',
        'projects': 'projects',
        'certificates': 'certificates',
        'social': 'social',
    }

    success_url = reverse_lazy('candidate:profile_complete')

    # ---------- helpers ----------
    def _get_current_step(self):
        return self.kwargs.get('step', 'personal')

    def _user_profile(self):
        return getattr(self.request.user, "profile", None)

    def _has_tokens(self, value):
        if not value:
            return False
        tokens = [t.strip() for t in str(value).split(',')]
        tokens = [t for t in tokens if t]
        return len(tokens) > 0

    def _split_tokens(self, value):
        if not value:
            return []
        parts = [p.strip().strip('"').strip("'") for p in str(value).strip().strip('[]').split(',')]
        return [p for p in parts if p]

    def _completion_map(self, profile: Profile):
        done = {k: False for k in self.STEPS_ORDER}
        if not profile:
            return done

        done['personal'] = all([
            bool(profile.first_name),
            bool(profile.last_name),
            bool(profile.gender),
            bool(profile.date_of_birth),
        ])

        done['professional'] = all([
            bool(profile.designation),
            bool(profile.experience_level),
            self._has_tokens(profile.sectors),
            self._has_tokens(profile.skills),
        ])

        done['address'] = all([
            bool(profile.phone_number),
            bool(profile.province),
            bool(profile.city),
        ])

        done['education'] = profile.educations.exists()
        is_entry = (profile.experience_level == 'entry')
        done['experience'] = True if is_entry else profile.experiences.exists()
        done['projects'] = profile.projects.exists()
        done['certificates'] = profile.certificates.exists()
        done['social'] = profile.social_links.exists()
        done['documents'] = bool(profile.resume)
        return done

    def _required_steps(self, profile: Profile):
        base_required = ['personal', 'professional', 'address', 'education']
        if not profile or profile.experience_level != 'entry':
            base_required.append('experience')
        return base_required

    def _calculate_progress(self, profile: Profile):
        completion = self._completion_map(profile)
        required = self._required_steps(profile)
        if not required:
            return 0
        completed = sum(1 for step in required if completion.get(step))
        return int(round((completed / len(required)) * 100))

    def _get_next_step(self, current_step):
        try:
            idx = self.STEPS_ORDER.index(current_step)
            if idx + 1 < len(self.STEPS_ORDER):
                return self.STEPS_ORDER[idx + 1]
        except ValueError:
            pass
        return None

    def _get_prev_step(self, current_step):
        try:
            idx = self.STEPS_ORDER.index(current_step)
            if idx - 1 >= 0:
                return self.STEPS_ORDER[idx - 1]
        except ValueError:
            pass
        return None

    # ---------- strong server validation per step ----------
    def _enforce_step_rules_or_error(self, step, form):
        """Return None if OK, otherwise a user-friendly error string."""
        if step == 'personal':
            cd = form.cleaned_data
            needed = ['first_name', 'last_name', 'gender', 'date_of_birth']
            if not all(cd.get(k) for k in needed):
                return "Please fill all required fields: First name, Last name, Gender, Date of birth."

        elif step == 'professional':
            cd = form.cleaned_data
            if not cd.get('designation') or not cd.get('experience_level'):
                return "Please provide your designation and experience level."
            if not cd.get('sectors') or not cd.get('skills'):
                return "Please add at least one sector and one skill."

        elif step == 'address':
            cd = form.cleaned_data
            if not cd.get('phone_number') or not cd.get('province') or not cd.get('city'):
                return "Phone number, Province and City are required."

        elif step == 'documents':
            cd = form.cleaned_data
            if not cd.get('resume'):
                return "Please upload your resume (PDF/DOC/DOCX)."

        return None

    # ---------- FormView overrides ----------
    def dispatch(self, request, *args, **kwargs):
        step = self._get_current_step()
        if step not in self.form_classes:
            raise Http404("Unknown profile step")

        profile = self._user_profile()
        if profile is None and step != 'personal':
            return redirect('candidate:profile', step='personal')

        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        step = self._get_current_step()
        return self.form_classes[step]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        profile = self._user_profile()
        if profile is not None:
            kwargs['instance'] = profile
        step = self._get_current_step()
        if step in self.FORMSET_STEPS:
            kwargs['prefix'] = self.FORMSET_PREFIX.get(step, step)
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        step = self._get_current_step()
        # Show exactly one blank row on GET if there are zero existing rows.
        if self.request.method == 'GET' and step in self.FORMSET_STEPS:
            try:
                initial_count = form.initial_form_count()
            except Exception:
                initial_count = 0
            if initial_count == 0:
                form.extra = 1
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        step = self._get_current_step()
        profile = self._user_profile()

        ctx['current_step'] = step
        ctx['progress'] = self._calculate_progress(profile)
        ctx['completion'] = self._completion_map(profile)
        ctx['steps'] = [
            ('personal', 'Personal Info'),
            ('professional', 'Professional Info'),
            ('address', 'Address'),
            ('education', 'Education'),
            ('experience', 'Experience'),
            ('projects', 'Projects'),
            ('certificates', 'Certificates'),
            ('social', 'Social Links'),
            ('documents', 'Documents'),
        ]
        ctx['formset_steps'] = self.FORMSET_STEPS
        ctx['prev_step'] = self._get_prev_step(step)
        ctx['next_step'] = self._get_next_step(step)

        # Sidebar preview needs the profile
        ctx['profile'] = profile
        if profile:
            ctx['sectors_list'] = self._split_tokens(profile.sectors)
            ctx['skills_list'] = self._split_tokens(profile.skills)
            ctx['counts'] = {
                'education': profile.educations.count(),
                'experience': profile.experiences.count(),
                'projects': profile.projects.count(),
                'certificates': profile.certificates.count(),
                'social': profile.social_links.count(),
            }
        else:
            ctx['sectors_list'] = []
            ctx['skills_list'] = []
            ctx['counts'] = {'education':0,'experience':0,'projects':0,'certificates':0,'social':0}

        if step in self.FORMSET_STEPS:
            ctx['formset'] = ctx.get('form')
            ctx['formset_prefix'] = self.FORMSET_PREFIX.get(step, step)

        return ctx

    # explicitly gate in POST so we never advance on incomplete steps
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        step = self._get_current_step()

        if not form.is_valid():
            return self.form_invalid(form)

        if step not in self.FORMSET_STEPS:
            rule_err = self._enforce_step_rules_or_error(step, form)
            if rule_err:
                form.add_error(None, rule_err)
                return self.form_invalid(form)

        if step in self.FORMSET_STEPS:
            def nonempty(form_row):
                cd = getattr(form_row, 'cleaned_data', {}) or {}
                if cd.get('DELETE'):
                    return False
                if step == 'education':
                    return bool(cd.get('institution') and cd.get('degree') and cd.get('start_date'))
                if step == 'experience':
                    return bool(cd.get('company_name') and cd.get('role') and cd.get('start_date'))
                if step == 'projects':
                    return bool(cd.get('title') and cd.get('description'))
                if step == 'social':
                    return bool(cd.get('platform') and cd.get('url'))
                if step == 'certificates':
                    return bool(cd.get('title'))
                return False

            rows = [f for f in form.forms if nonempty(f)]
            count = len(rows)

            if step == 'education' and count < 1:
                form.add_error(None, "Please add at least one education entry.")
                return self.form_invalid(form)

            if step == 'experience':
                profile = self._user_profile()
                is_entry = profile and profile.experience_level == 'entry'
                if not is_entry and count < 1:
                    form.add_error(None, "Please add at least one experience or change your level to Entry.")
                    return self.form_invalid(form)

            if step == 'projects' and count < 1:
                form.add_error(None, "Please add at least one project (title and description).")
                return self.form_invalid(form)

            if step == 'social':
                has_li_or_gh = any(
                    (getattr(f, 'cleaned_data', {}).get('platform') in ('linkedin', 'github')) and
                    getattr(f, 'cleaned_data', {}).get('url') and not
                    getattr(f, 'cleaned_data', {}).get('DELETE')
                    for f in form.forms
                )
                if not has_li_or_gh:
                    form.add_error(None, "Please add at least one LinkedIn or GitHub link.")
                    return self.form_invalid(form)

        return self.form_valid(form)

    def form_valid(self, form):
        step = self._get_current_step()
        profile = self._user_profile()

        if step in self.FORMSET_STEPS:
            form.instance = profile
            form.save()
            messages.success(self.request, f"{step.capitalize()} information saved successfully!")
        else:
            obj = form.save(commit=False)
            if profile is None:
                obj.user = self.request.user
            obj.save()
            messages.success(self.request, f"{step.capitalize()} information saved successfully!")

        next_step = self._get_next_step(step)
        if next_step:
            return redirect('candidate:profile', step=next_step)
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please fix the errors below to continue.")
        return self.render_to_response(self.get_context_data(form=form))


class ProfileCompleteView(TemplateView):
    template_name = 'candidate/profile_complete.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['profile'] = getattr(self.request.user, "profile", None)
        return ctx


class ProfilePreviewView(LoginRequiredMixin, TemplateView):
    """
    Read-only summary with edit buttons for each section.
    """
    template_name = 'candidate/profile_preview.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = getattr(self.request.user, "profile", None)
        ctx['profile'] = profile
        if profile:
            ctx['educations'] = profile.educations.order_by('-start_date', '-end_date', '-id')
            ctx['experiences'] = profile.experiences.order_by('-start_date', '-end_date', '-id')
            ctx['projects'] = profile.projects.order_by('-start_date', '-end_date', '-id')
            ctx['certificates'] = profile.certificates.order_by('-date', '-id')
            ctx['social_links'] = profile.social_links.all()
            # tokenized
            def split_tokens(value):
                if not value:
                    return []
                parts = [p.strip().strip('"').strip("'") for p in str(value).strip().strip('[]').split(',')]
                return [p for p in parts if p]
            ctx['sectors_list'] = split_tokens(profile.sectors)
            ctx['skills_list'] = split_tokens(profile.skills)
        else:
            ctx['educations'] = []
            ctx['experiences'] = []
            ctx['projects'] = []
            ctx['certificates'] = []
            ctx['social_links'] = []
            ctx['sectors_list'] = []
            ctx['skills_list'] = []
        return ctx

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render
from recommendations.simple_hybrid import recommend_jobs_for_candidate
from django.utils import timezone

@login_required
def recommended_demo(request):
    """
    Build a list of recommendation items with safe defaults so the template
    can render without relying on filters like default:[] for lists.
    """
    recs = recommend_jobs_for_candidate(request.user, limit=20)

    items = []
    today = timezone.now().date()

    for r in recs:
        ct = ContentType.objects.get_for_id(r.ct_id)
        obj = ct.get_object_for_this_type(id=r.obj_id)  # JobPost or InternshipPost

        # Try to use existing days_left; if missing, compute from application_deadline
        obj_days_left = getattr(obj, "days_left", None)
        deadline = getattr(obj, "application_deadline", None)

        if obj_days_left is None and deadline:
            try:
                computed_days_left = (deadline - today).days
            except Exception:
                computed_days_left = None
        else:
            computed_days_left = obj_days_left

        items.append({
            "obj": obj,
            "score": getattr(r, "score", None),
            "why": getattr(r, "why", ""),
            "ct_id": r.ct_id,
            # May be None → template handles that gracefully
            "matched_skills": getattr(r, "matched_skills", None),
            "missing_skills": getattr(r, "missing_skills", None),
            "days_left": computed_days_left,
        })

    return render(
        request,
        "candidate/recommended_demo.html",
        {"recommended_jobs": items}
    )