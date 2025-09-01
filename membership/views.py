from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.urls import reverse

from django.conf import settings

from .models import CompanyWallet, WalletTransaction, OrderStatus, PayMethod, Order
from .services import create_order, finalize_paid_order, _compute_totals
from membership.services import get_spendable_balance

@login_required
def membership_home(request):
    company = request.user.company_profile
    # ensure a wallet row exists (won't duplicate)
    CompanyWallet.objects.get_or_create(company=company)

    # show *spendable* credits (excludes expired)
    balance = get_spendable_balance(company)

    txns = (WalletTransaction.objects
            .filter(company=company)
            .order_by("-created_at")[:25])

    return render(request, "membership/home.html", {
        "balance": balance,
        "transactions": txns,
        "job_cost": getattr(settings, "CREDITS_JOB_POST", 10),
    })

@login_required
def credits_select(request):
    # You can read qty via GET ?qty=200 and prefill the slider in template
    qty = int(request.GET.get("qty", 200))
    pricing = _compute_totals(qty)
    return render(request, "membership/credits_select.html", {
        "qty": qty,
        "pricing": pricing,
        "discounts": getattr(settings, "CREDIT_DISCOUNTS", {}),
        "unit_rupees": getattr(settings, "CREDITS_UNIT_PRICE_RUPEES", 10),
        "vat_percent": getattr(settings, "VAT_PERCENT", 13),
    })

@login_required
def checkout(request):
    if request.method == "POST":
        qty = int(request.POST.get("qty", "0"))
        method = request.POST.get("method")  # 'KHALTI' | 'ESEWA' | 'BANK' | 'QR'
        if qty <= 0 or method not in dict(PayMethod.choices):
            return HttpResponseBadRequest("Invalid request")

        order = create_order(request.user.company_profile, qty, method)
        # For BANK/QR, you’ll show static details + ask for receipt upload.
        # For KHALTI/eSewa, you will redirect/initiate (to be implemented next).
        messages.info(request, f"Order {order.code} created for {qty} credits.")
        return redirect(reverse("membership:home"))
    else:
        # Usually you’ll arrive here with POST; GET can render a simple pick-a-method page
        return render(request, "membership/checkout.html")

# ——— Gateway callback placeholders ———
@login_required
def khalti_return(request):
    # TODO: verify pidx server-side, then:
    # finalize_paid_order(order, provider_ref=pidx, amount_paisa=verified_amount, payload=lookup_payload)
    messages.success(request, "Khalti payment received. Credits added.")
    return redirect(reverse("membership:home"))

@login_required
def esewa_success(request):
    # TODO: verify HMAC / status check, then finalize_paid_order(...)
    messages.success(request, "eSewa payment received. Credits added.")
    return redirect(reverse("membership:home"))

@login_required
def esewa_failure(request):
    messages.error(request, "Payment failed or cancelled on eSewa.")
    return redirect(reverse("membership:home"))

@login_required
def upload_receipt(request):
    # Your modal/file upload handler. After manual verification by admin,
    # call finalize_paid_order(order, provider_ref="BANK/QR", amount_paisa=order.total_paisa, payload={...})
    messages.info(request, "Receipt uploaded. We’ll verify and credit soon.")
    return redirect(reverse("membership:home"))
