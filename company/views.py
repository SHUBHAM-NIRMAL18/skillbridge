from django.shortcuts import render

def dashboard_view(request):
    return render(request, 'dashboard.html')

def alljobs_view(request):
    return render(request, 'all_jobs.html')

def post_choice_view(request):
    return render(request, 'post_choice.html')