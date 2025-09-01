from datetime import timedelta
from typing import Optional, Tuple, List
from uuid import uuid4

from django.conf import settings
from django.db import transaction, models
from django.utils import timezone

from .models import (
    CompanyWallet, CreditBatch, WalletTransaction, TxnType, CreditSource,
    Order, OrderStatus, PayMethod, Payment, PaymentStatus
)

# ——— Wallet helpers ———
def _get_or_create_wallet(company):
    wallet, _ = CompanyWallet.objects.get_or_create(company=company)
    return wallet

def get_spendable_balance(company) -> int:
    now = timezone.now()
    total = (CreditBatch.objects
             .filter(company=company)
             .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
             .aggregate(s=models.Sum("credits_remaining"))["s"])
    return total or 0

def can_spend(company, amount: int) -> Tuple[bool, int]:
    bal = get_spendable_balance(company)
    return (bal >= amount), max(0, amount - bal)

@transaction.atomic
def grant_credits(
    company, amount: int, *, source: str, note: str = "",
    expires_in_days: Optional[int] = None, meta: Optional[dict] = None,
):
    if amount < 0:
        raise ValueError("grant amount must be non-negative")

    wallet = _get_or_create_wallet(company)
    expires_at = None
    if expires_in_days:
        expires_at = timezone.now() + timedelta(days=expires_in_days)

    batch = CreditBatch.objects.create(
        company=company,
        source=source,
        credits_total=amount,
        credits_remaining=amount,
        expires_at=expires_at,
    )

    wallet.balance_credits = wallet.balance_credits + amount
    wallet.save(update_fields=["balance_credits", "updated_at"])

    txn = WalletTransaction.objects.create(
        company=company,
        txn_type=TxnType.GRANT,
        credits_delta=amount,
        balance_after=wallet.balance_credits,
        reason=note or f"{source} grant",
        meta=meta or {},
    )
    return batch, txn

@transaction.atomic
def spend_credits(company, amount: int, *, reason: str, idempotency_key: Optional[str] = None, meta: Optional[dict] = None):
    if amount <= 0:
        raise ValueError("spend amount must be positive")

    # idempotency shortcut
    if idempotency_key:
        existing = WalletTransaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing

    ok, missing = can_spend(company, amount)
    if not ok:
        raise ValueError(f"INSUFFICIENT_CREDITS:{amount}:{missing}")

    wallet = _get_or_create_wallet(company)

    now = timezone.now()
    batches = (CreditBatch.objects
               .select_for_update()
               .filter(company=company)
               .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
               .order_by("expires_at", "id"))

    to_deduct = amount
    consumed: List[int] = []

    for b in batches:
        if to_deduct <= 0:
            break
        take = min(b.credits_remaining, to_deduct)
        if take > 0:
            b.credits_remaining -= take
            b.save(update_fields=["credits_remaining"])
            to_deduct -= take
            consumed.append(b.id)

    if to_deduct != 0:
        raise RuntimeError("Credit deduction mismatch")

    wallet.balance_credits -= amount
    wallet.save(update_fields=["balance_credits", "updated_at"])

    txn = WalletTransaction.objects.create(
        company=company,
        txn_type=TxnType.DEBIT,
        credits_delta=-amount,
        balance_after=wallet.balance_credits,
        reason=reason,
        meta=meta or {},
        idempotency_key=idempotency_key,
        consumed_batches=consumed
    )
    return txn

# Called from company job-post flow
def charge_for_job_post(company, *, meta=None):
    cost = getattr(settings, "CREDITS_JOB_POST", 10)
    return spend_credits(company, cost, reason="JOB_POST_CREATE", meta=meta or {})

# ——— Order helpers (for Buy Credits screen) ———
def _compute_totals(qty: int) -> dict:
    unit = int(getattr(settings, "CREDITS_UNIT_PRICE_RUPEES", 10)) * 100  # paisa
    disc_map = getattr(settings, "CREDIT_DISCOUNTS", {})
    discount_pct = int(disc_map.get(qty, 0))
    vat_pct = int(getattr(settings, "VAT_PERCENT", 13))
    base = qty * unit
    after_disc = base - (base * discount_pct) // 100
    vat = (after_disc * vat_pct) // 100
    total = after_disc + vat
    return {
        "unit_price_paisa": unit, "discount_percent": discount_pct, "vat_percent": vat_pct,
        "subtotal_paisa": after_disc, "total_paisa": total
    }

def create_order(company, qty: int, method: str) -> Order:
    code = f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}-{str(uuid4())[:8].upper()}"
    totals = _compute_totals(qty)
    return Order.objects.create(
        code=code, company=company, credits_qty=qty, method=method, status=OrderStatus.PENDING, **totals
    )

@transaction.atomic
def finalize_paid_order(order: Order, *, provider_ref: str, amount_paisa: int, payload: dict):
    # idempotent: if already PAID, just return
    if order.status == OrderStatus.PAID:
        return order

    # basic safety: amounts must match
    if int(amount_paisa) != int(order.total_paisa):
        raise ValueError("AMOUNT_MISMATCH")

    order.status = OrderStatus.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at"])

    # mark payment as completed (create if missing)
    payment, _ = Payment.objects.get_or_create(order=order, defaults={
        "method": order.method, "requested_amount_paisa": order.total_paisa
    })
    payment.status = PaymentStatus.COMPLETED
    payment.verified_amount_paisa = amount_paisa
    payment.provider_ref = provider_ref
    payment.raw_payload = payload or {}
    payment.verified_at = timezone.now()
    payment.save()

    # grant purchased credits (non-expiring)
    grant_credits(order.company, order.credits_qty, source=CreditSource.TOPUP, note=f"Order {order.code}")
    return order
