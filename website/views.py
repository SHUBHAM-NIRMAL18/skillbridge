from django.shortcuts import render

# Create your views here.
def home_view(request):
    """
    Render the home page.
    """
    return render(request, 'index.html')

def login_view(request):
    """
    Render the login page.
    """
    return render(request, 'accounts/login.html')

def privacy_policy_view(request):
    """
    Render the privacy policy page.
    """
    return render(request, 'privacy.html')


def termcondition_view(request):
    """
    Render the terms and conditions page.
    """
    return render(request, 'termcondition.html')

def internship_view(request):
    """
    Render the internship page.
    """
    return render(request, 'internship.html')

def fullinternship_view(request):
    """
    Render the view internship page.
    """
    return render(request, 'view-intern.html')