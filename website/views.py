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
