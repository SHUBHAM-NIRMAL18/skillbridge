from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.templatetags.static import static

from .models import CompanyWallet, WalletTransaction, OrderStatus, PayMethod, Order, Payment, PaymentStatus
from .services import (
    create_order, finalize_paid_order, _compute_totals, get_spendable_balance,
    khalti_initiate, khalti_lookup,
)


# ------------------------
# Membership Home (balance + history)
# ------------------------
@login_required
def membership_home(request):
    company = request.user.company_profile
    CompanyWallet.objects.get_or_create(company=company)
    balance = get_spendable_balance(company)
    txns = WalletTransaction.objects.filter(company=company).order_by("-created_at")[:25]
    return render(request, "membership/home.html", {
        "balance": balance,
        "transactions": txns,
        "job_cost": getattr(settings, "CREDITS_JOB_POST", 10),
    })


# ------------------------
# Step 1: Credit packs selector
# ------------------------
@login_required
def credits_select(request):
    packs = list(getattr(settings, "CREDIT_PACKS", [50, 200, 500, 1000, 5000, 10000]))
    selected = int(request.GET.get("qty", packs[0]))
    options = []
    for q in packs:
        pricing = _compute_totals(q)
        options.append({
            "qty": q,
            "discount_percent": pricing["discount_percent"],
            "vat_percent": pricing["vat_percent"],
            "total_paisa": pricing["total_paisa"],
            "total_rupees": pricing["total_paisa"] // 100,
        })
    selected_pricing = _compute_totals(selected)
    return render(request, "membership/credits_select.html", {
        "packs": packs,
        "options": options,
        "qty": selected,
        "selected_total_rupees": selected_pricing["total_paisa"] // 100,
        "unit_rupees": getattr(settings, "CREDITS_UNIT_PRICE_RUPEES", 10),
        "vat_percent": getattr(settings, "VAT_PERCENT", 13),
        "job_cost": getattr(settings, "CREDITS_JOB_POST", 10),
    })


# ------------------------
# Step 2: Review & pay (method selector)
#   GET  -> summary + choose method
#   POST -> create order + branch by method
# ------------------------
@login_required
def checkout(request):
    packs = list(getattr(settings, "CREDIT_PACKS", [50, 200, 500, 1000, 5000, 10000]))
    if request.method == "GET":
        # qty via query param (from Step 1)
        qty = int(request.GET.get("qty", packs[0]))
        if qty not in packs:
            messages.error(request, "Invalid credit pack.")
            return redirect(reverse("membership:select"))

        pricing = _compute_totals(qty)
        # Rupee breakdown for clean display
        unit_rupees = pricing["unit_price_paisa"] // 100
        base_rupees = (qty * pricing["unit_price_paisa"]) // 100
        discount_rupees = (qty * pricing["unit_price_paisa"] - pricing["subtotal_paisa"]) // 100
        vat_rupees = (pricing["total_paisa"] - pricing["subtotal_paisa"]) // 100
        total_rupees = pricing["total_paisa"] // 100

        return render(request, "membership/checkout.html", {
            "qty": qty,
            "pricing": pricing,
            "unit_rupees": unit_rupees,
            "base_rupees": base_rupees,
            "discount_rupees": discount_rupees,
            "vat_rupees": vat_rupees,
            "total_rupees": total_rupees,
            "job_cost": getattr(settings, "CREDITS_JOB_POST", 10),  
        })

    # POST: create order + branch by method
    qty = int(request.POST.get("qty", "0"))
    method = (request.POST.get("method") or "").upper()
    if qty not in packs:
        return HttpResponseBadRequest("Invalid pack.")
    if method not in (PayMethod.KHALTI, PayMethod.ESEWA, PayMethod.BANK, PayMethod.QR):
        return HttpResponseBadRequest("Invalid method.")

    company = request.user.company_profile
    order = create_order(company, qty, method)

    # Persist a Payment row upfront for consistency
    Payment.objects.update_or_create(
        order=order,
        defaults={
            "method": method,
            "status": PaymentStatus.INITIATED,
            "requested_amount_paisa": order.total_paisa,
        },
    )

    # KHALTI → initiate + redirect
    if method == PayMethod.KHALTI:
        try:
            data = khalti_initiate(order)
            payment_url = data.get("payment_url")
            if not payment_url:
                raise ValueError("Missing payment_url from Khalti initiate")
            return redirect(payment_url)
        except Exception as e:
            order.status = OrderStatus.FAILED
            order.save(update_fields=["status"])
            msg = "Could not initiate Khalti payment."
            if getattr(settings, "DEBUG", False):
                msg += f" Details: {e}"
            messages.error(request, msg)
            return redirect(reverse("membership:select"))

    # eSewa → (placeholder for now)
    if method == PayMethod.ESEWA:
        messages.info(request, "eSewa checkout is coming soon. Choose Khalti or Bank/QR for now.")
        # Keep order pending
        return redirect(f"{reverse('membership:checkout')}?qty={qty}")

    # Bank/QR → show instructions page (no redirect to gateway)
    # Treat QR as Bank for manual verification
    return redirect(reverse("membership:bank_order", args=[order.code]))


# ------------------------
# Khalti return (lookup by pidx first → finalize)
# ------------------------
@login_required
def khalti_return(request):
    pidx = request.GET.get("pidx")
    if not pidx:
        messages.error(request, "Missing Khalti reference.")
        return redirect(reverse("membership:home"))

    try:
        # Resolve via PIDX → Payment → Order
        payment = (Payment.objects.select_related("order")
                   .filter(provider_ref=pidx).first())
        order = payment.order if payment else None

        data = khalti_lookup(pidx)
        status = data.get("status")
        total_amount = int(data.get("total_amount") or 0)
        poid = data.get("purchase_order_id")

        if not order and poid:
            order = Order.objects.filter(code=poid).first()

        if not order:
            messages.error(request, f"Order not found for reference PIDX={pidx}.")
            return redirect(reverse("membership:home"))

        # Ownership check
        if getattr(order, "company_id", None) != getattr(request.user.company_profile, "id", None):
            messages.error(request, "This payment does not belong to your account.")
            return redirect(reverse("membership:home"))

        if status == "Completed" and total_amount == int(order.total_paisa):
            finalize_paid_order(order, provider_ref=pidx, amount_paisa=order.total_paisa, payload=data)
            messages.success(request, f"Payment received. {order.credits_qty} credits added.")
        else:
            order.status = OrderStatus.FAILED
            order.save(update_fields=["status"])
            msg = "Payment could not be verified."
            if getattr(settings, "DEBUG", False):
                msg += f" [status={status}, total={total_amount}, expected={order.total_paisa}]"
            messages.error(request, msg)

    except Exception as e:
        msg = "Payment verification failed."
        if getattr(settings, "DEBUG", False):
            msg += f" Details: {e}"
        messages.error(request, msg)

    return redirect(reverse("membership:home"))


# ------------------------
# Bank/QR order instructions page
# ------------------------
@login_required
def bank_order(request, code: str):
    order = get_object_or_404(Order, code=code, company=request.user.company_profile)
    if order.method not in (PayMethod.BANK, PayMethod.QR):
        messages.error(request, "This order is not a Bank/QR payment.")
        return redirect(reverse("membership:home"))

    # Only pass the order and computed amount; the template will show static bank details.
    ctx = {
        "order": order,
        "amount_rupees": order.total_paisa // 100,
    }
    return render(request, "membership/bank_order.html", ctx)


# ------------------------
# Receipt upload stub (unchanged)
# ------------------------
@login_required
def upload_receipt(request):
    messages.info(request, "Receipt upload coming soon. For now, email support with your proof of payment.")
    return redirect(reverse("membership:home"))



# ------------------------
# Receipt PDF generation (simple HTML to PDF via browser)  
# ------------------------
@login_required
def receipt_pdf(request, code: str):
    order = get_object_or_404(Order, code=code, company=request.user.company_profile)
    if order.status != OrderStatus.PAID:
        messages.error(request, "Receipt is available only after payment is confirmed.")
        return redirect("membership:home")

    logo_url = request.build_absolute_uri(static("icons/sb-logo.png"))

    unit_rupees = order.unit_price_paisa // 100
    base_rupees = (order.credits_qty * order.unit_price_paisa) // 100
    subtotal_rupees = order.subtotal_paisa // 100            # after discount, before VAT
    discount_rupees = base_rupees - subtotal_rupees          # discount amount
    vat_rupees = (order.total_paisa - order.subtotal_paisa) // 100
    total_rupees = order.total_paisa // 100

    ctx = {
        "order": order,
        "company_display": getattr(order.company, "name", "")
                           or f"{getattr(order.company, 'first_name', '')} {getattr(order.company, 'last_name','')}".strip()
                           or "Your Company",
        "logo_url": logo_url,
        "unit_rupees": unit_rupees,
        "base_rupees": base_rupees,
        "subtotal_rupees": subtotal_rupees,
        "discount_rupees": discount_rupees,
        "vat_rupees": vat_rupees,
        "total_rupees": total_rupees,
        "vat_percent": order.vat_percent,
        "discount_percent": order.discount_percent,
        "paid_at": order.paid_at,
    }

    html = render_to_string("membership/receipt.html", ctx)
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="Receipt-{order.code}.pdf"'
        return resp
    except Exception:
        return HttpResponse(html)
