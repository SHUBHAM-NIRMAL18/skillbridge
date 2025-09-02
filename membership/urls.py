from django.urls import path
from . import views

app_name = "membership"

urlpatterns = [
    path("", views.membership_home, name="home"),
    path("credits/select/", views.credits_select, name="select"),
    path("checkout/", views.checkout, name="checkout"),  # Step 2: review + method
    path("khalti/return/", views.khalti_return, name="khalti_return"),
    path("order/<str:code>/bank/", views.bank_order, name="bank_order"),  # NEW
    path("receipt/upload/", views.upload_receipt, name="upload_receipt"),
]
