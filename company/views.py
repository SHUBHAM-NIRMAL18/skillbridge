from django.shortcuts import render

def dashboard_view(request):
    return render(request, 'company/dashboard.html')

def alljobs_view(request):
    return render(request, 'company/all_jobs.html')

def post_choice_view(request):
    return render(request, 'company/post_choice.html')