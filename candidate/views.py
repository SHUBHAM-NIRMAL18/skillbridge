from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView

from .forms import (
    PersonalInfoForm, ProfessionalInfoForm, AddressInfoForm,
    EducationFormSet, ExperienceFormSet, ProjectFormSet,
    CertificateFormSet, SocialLinkFormSet, DocumentUploadForm
)
from .models import Profile


@login_required
def candidate_dashboard(request):
    # (Optional) Enforce role-matching:
    if getattr(request.user, "role", None) != getattr(request.user, "ROLE_CANDIDATE", None):
        return redirect('accounts:login')
    return render(request, 'candidate/dashboard.html')


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

    # Explicit prefixes for formsets so POST names match EXACTLY
    FORMSET_PREFIX = {
        'education': 'education',
        'experience': 'experience',
        'projects': 'projects',
        'certificates': 'certificates',
        'social': 'social',
    }

    success_url = reverse_lazy('candidate:profile_complete')

    # ————— helpers —————
    def _get_current_step(self):
        return self.kwargs.get('step', 'personal')

    def _user_profile(self):
        # Returns Profile instance or None
        return getattr(self.request.user, "profile", None)

    # ---- completion + progress ------------------------------------------------
    def _has_tokens(self, value):
        if not value:
            return False
        tokens = [t.strip() for t in str(value).split(',')]
        tokens = [t for t in tokens if t]
        return len(tokens) > 0

    def _completion_map(self, profile: Profile):
        done = {k: False for k in self.STEPS_ORDER}
        if not profile:
            return done

        # personal: required fields present
        personal_ok = all([
            bool(profile.first_name),
            bool(profile.last_name),
            bool(profile.gender),
            bool(profile.date_of_birth),
        ])
        done['personal'] = personal_ok

        # professional: designation, experience_level, and at least one sector & skill
        professional_ok = all([
            bool(profile.designation),
            bool(profile.experience_level),
            self._has_tokens(profile.sectors),
            self._has_tokens(profile.skills),
        ])
        done['professional'] = professional_ok

        # address: phone, province & city required
        address_ok = all([
            bool(profile.phone_number),
            bool(profile.province),
            bool(profile.city),
        ])
        done['address'] = address_ok

        # education: at least one row
        done['education'] = profile.educations.exists()

        # experience: conditionally required
        is_entry = (profile.experience_level == 'entry')
        done['experience'] = True if is_entry else profile.experiences.exists()

        # optional sections
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
        pct = int(round((completed / len(required)) * 100))
        return pct

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

    # ————— FormView overrides —————
    def dispatch(self, request, *args, **kwargs):
        step = self._get_current_step()
        if step not in self.form_classes:
            raise Http404("Unknown profile step")

        profile = self._user_profile()

        # If no profile exists yet, force users to start at 'personal' step.
        if profile is None and step != 'personal':
            return redirect('candidate:profile', step='personal')

        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        step = self._get_current_step()
        return self.form_classes[step]

    def get_form_kwargs(self):
        """
        Ensure both ModelForms and InlineFormSets get the profile instance (if exists).
        Also set a STABLE prefix for formsets so names match management form.
        """
        kwargs = super().get_form_kwargs()
        profile = self._user_profile()
        if profile is not None:
            kwargs['instance'] = profile  # works for inline formsets too

        step = self._get_current_step()
        if step in self.FORMSET_STEPS:
            kwargs['prefix'] = self.FORMSET_PREFIX.get(step, step)

        return kwargs

    def get_form(self, form_class=None):
        """
        Build the form/formset. For formset steps on GET with zero existing rows,
        temporarily set `extra = 1` so exactly one blank row is shown by default.
        """
        form = super().get_form(form_class)
        step = self._get_current_step()

        if self.request.method == 'GET' and step in self.FORMSET_STEPS:
            # If there are no existing child objects, show one blank form (and only one).
            try:
                initial_count = form.initial_form_count()
            except Exception:
                initial_count = 0
            if initial_count == 0:
                # IMPORTANT: set extra BEFORE the template accesses form.forms/management_form
                form.extra = 1

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        step = self._get_current_step()
        profile = self._user_profile()

        completion = self._completion_map(profile)
        progress = self._calculate_progress(profile)

        context['current_step'] = step
        context['progress'] = progress
        context['completion'] = completion
        context['steps'] = [
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
        context['formset_steps'] = self.FORMSET_STEPS
        context['prev_step'] = self._get_prev_step(step)
        context['next_step'] = self._get_next_step(step)

        # If this is a formset step, expose the bound form as "formset" for the template.
        if step in self.FORMSET_STEPS:
            context['formset'] = context.get('form')
            context['formset_prefix'] = self.FORMSET_PREFIX.get(step, step)

        return context

    def form_valid(self, form):
        step = self._get_current_step()
        profile = self._user_profile()

        if step in self.FORMSET_STEPS:
            # Must have a profile instance (dispatch enforces personal first)
            form.instance = profile

            # Experience is conditionally required
            if step == 'experience':
                is_entry = (profile and profile.experience_level == 'entry')
                valid_rows = 0
                for f in form.forms:
                    if getattr(f, 'cleaned_data', None) and not f.cleaned_data.get('DELETE', False):
                        if f.cleaned_data.get('company_name') and f.cleaned_data.get('role'):
                            valid_rows += 1
                if not is_entry and valid_rows == 0:
                    form.add_error(None, "Please add at least one experience or mark your level as Entry.")
                    return self.form_invalid(form)

            form.save()
            messages.success(self.request, f"{step.capitalize()} information saved successfully!")

        else:
            # ModelForm: safe create/update
            obj = form.save(commit=False)
            if profile is None:
                obj.user = self.request.user
            obj.save()
            messages.success(self.request, f"{step.capitalize()} information saved successfully!")

        next_step = self._get_next_step(step)
        if next_step:
            return redirect('candidate:profile', step=next_step)
        return super().form_valid(form)


class ProfileCompleteView(TemplateView):
    template_name = 'candidate/profile_complete.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['profile'] = getattr(self.request.user, "profile", None)
        return ctx


# =========================
# HTMX: add a new inline formset row
# =========================
class ProfileFormsetAddRowView(LoginRequiredMixin, View):
    """
    Returns one new, correctly-indexed formset row HTML for a given step.
    Expects query params:
      - index: current TOTAL_FORMS before adding (we render the next index)
    """
    FORMSET_STEPS = ['education', 'experience', 'projects', 'certificates', 'social']

    FORMSET_PREFIX = {
        'education': 'education',
        'experience': 'experience',
        'projects': 'projects',
        'certificates': 'certificates',
        'social': 'social',
    }

    # map step -> partial template path
    PARTIAL_TEMPLATES = {
        'education': 'candidate/partials/education_form_row.html',
        'experience': 'candidate/partials/experience_form_row.html',
        'projects': 'candidate/partials/projects_form_row.html',
        'certificates': 'candidate/partials/certificates_form_row.html',
        'social': 'candidate/partials/social_form_row.html',
    }

    # which formset class to use
    FORMSET_CLASS = {
        'education': EducationFormSet,
        'experience': ExperienceFormSet,
        'projects': ProjectFormSet,
        'certificates': CertificateFormSet,
        'social': SocialLinkFormSet,
    }

    def get(self, request, *args, **kwargs):
        step = kwargs.get('step')
        if step not in self.FORMSET_STEPS:
            raise Http404("Unknown formset step")

        # must have a profile
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return HttpResponseBadRequest("Profile not initialized")

        # read the current count from the client (TOTAL_FORMS before adding)
        try:
            current_count = int(request.GET.get('index', '0'))
            if current_count < 0:
                current_count = 0
        except ValueError:
            current_count = 0

        prefix = self.FORMSET_PREFIX[step]
        formset_cls = self.FORMSET_CLASS[step]
        base_form_class = formset_cls.form
        per_form_prefix = f"{prefix}-{current_count}"

        # Create a blank child form for the new row
        form = base_form_class(prefix=per_form_prefix)

        # Render partial
        html = render_to_string(
            self.PARTIAL_TEMPLATES[step],
            {'f': form, 'prefix': prefix, 'index': current_count},
            request=request
        )
        return render(request, self.PARTIAL_TEMPLATES[step], {'f': form, 'prefix': prefix, 'index': current_count})
