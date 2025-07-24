from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CompanyProfileForm
from django.contrib import messages
from .models import CompanyProfile

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