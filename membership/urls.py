from django.urls import path
from . import views

app_name = "membership"

urlpatterns = [
    path("", views.membership_home, name="home"),
    path("credits/select/", views.credits_select, name="select"),
    path("checkout/", views.checkout, name="checkout"),
    path("khalti/return/", views.khalti_return, name="khalti_return"),
    path("receipt/<str:code>/", views.receipt_pdf, name="receipt_pdf"),
    path("order/<str:code>/bank/", views.bank_order, name="bank_order"),
    path("receipt/upload/", views.upload_receipt, name="upload_receipt"),

    path("esewa/success/", views.esewa_success, name="esewa_success"),
    path("esewa/failure/", views.esewa_failure, name="esewa_failure"),
]
