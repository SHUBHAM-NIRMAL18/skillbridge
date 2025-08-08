from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView
from django.http import Http404

from .forms import (
    PersonalInfoForm, ProfessionalInfoForm, AddressInfoForm,
    EducationFormSet, ExperienceFormSet, ProjectFormSet,
    CertificateFormSet, SocialLinkFormSet, DocumentUploadForm
)


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

    success_url = reverse_lazy('candidate:profile_complete')

    # ————— helpers —————
    def _get_current_step(self):
        return self.kwargs.get('step', 'personal')

    def _calculate_progress(self, current_step):
        try:
            idx = self.STEPS_ORDER.index(current_step)
            return int((idx + 1) / len(self.STEPS_ORDER) * 100)
        except ValueError:
            return 0

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
    def get_form_class(self):
        step = self._get_current_step()
        return self.form_classes[step]

    def get_form_kwargs(self):
        """
        Ensure both ModelForms and InlineFormSets get the profile instance.
        FormView will also inject POST/FILES into kwargs on POST automatically.
        """
        kwargs = super().get_form_kwargs()
        profile = getattr(self.request.user, "profile", None)
        if profile is not None:
            kwargs['instance'] = profile  # works for inline formsets too
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        step = self._get_current_step()

        context['current_step'] = step
        context['progress'] = self._calculate_progress(step)
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

        return context

    def form_valid(self, form):
        step = self._get_current_step()

        if step in self.FORMSET_STEPS:
            # 'form' is a bound inline formset here
            form.instance = self.request.user.profile
            form.save()
            messages.success(self.request, f"{step.capitalize()} information saved successfully!")
        else:
            # 'form' is a bound ModelForm
            form.instance = self.request.user.profile
            form.save()
            messages.success(self.request, f"{step.capitalize()} information saved successfully!")

        next_step = self._get_next_step(step)
        if next_step:
            return redirect('candidate:profile', step=next_step)
        return super().form_valid(form)
    

    def dispatch(self, request, *args, **kwargs):
        step = self._get_current_step()
        if step not in self.form_classes:
            # either send them to complete, or 404
            # return redirect('candidate:profile_complete')
            raise Http404("Unknown profile step")
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        step = self._get_current_step()
        return self.form_classes[step]


class ProfileCompleteView(TemplateView):
    template_name = 'candidate/profile_complete.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['profile'] = getattr(self.request.user, "profile", None)
        return ctx
