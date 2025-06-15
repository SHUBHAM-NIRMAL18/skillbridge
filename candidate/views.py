from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def candidate_dashboard(request):
    # (Optional) Enforce role-matching:
    if request.user.role != request.user.ROLE_CANDIDATE:
        return redirect('accounts:login')

    return render(request, 'candidate/dashboard.html')
