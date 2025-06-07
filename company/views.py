from django.shortcuts import render

def dashboard_view(request):
    return render(request, 'dashboard.html')

def alljobs_view(request):
    return render(request, 'all_jobs.html')