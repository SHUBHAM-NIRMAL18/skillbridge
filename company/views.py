from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

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