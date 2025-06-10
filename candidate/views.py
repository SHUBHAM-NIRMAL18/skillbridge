from django.shortcuts import render

# Create your views here.
def candidate_dashboard(request):
    """
    Render the candidate dashboard.
    """
    return render(request, 'candidate/dashboard.html')
