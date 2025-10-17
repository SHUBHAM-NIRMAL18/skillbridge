# membership/services.py
import json
from uuid import uuid4
import requests
import logging

from django.conf import settings
from django.db import transaction, models
from django.db.models import F
from django.urls import reverse
from django.utils import timezone

from .models import (
    CompanyWallet, CreditBatch, WalletTransaction,
    TxnType, CreditSource,
    Order, OrderStatus, PayMethod,
    Payment, PaymentStatus,
)

logger = logging.getLogger(__name__)


def _get_or_create_wallet(company, *, for_update: bool = False) -> CompanyWallet:
    """
    Get/create the wallet. Optionally lock the row for an in-flight balance update.
    """
    # get_or_create() can't be combined with select_for_update(create=True),
    # so we do it in two steps safely inside atomic transactions where needed.
    wallet, created = CompanyWallet.objects.get_or_create(company=company)
    if for_update:
        # Lock the row after ensuring it exists
        wallet = CompanyWallet.objects.select_for_update().get(pk=wallet.pk)
    return wallet


def get_spendable_balance(company) -> int:
    now = timezone.now()
    total = (
        CreditBatch.objects
        .filter(company=company)
        .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
        .aggregate(s=models.Sum("credits_remaining"))["s"]
    )
    return total or 0


@transaction.atomic
def grant_credits(company, amount: int, *, source: str, note: str = "", expires_in_days=None, meta=None):
    if amount < 0:
        raise ValueError("grant amount must be non-negative")

    wallet = _get_or_create_wallet(company, for_update=True)

    expires_at = None
    if expires_in_days:
        expires_at = timezone.now() + timezone.timedelta(days=int(expires_in_days))

    batch = CreditBatch.objects.create(
        company=company,
        source=source,
        credits_total=amount,
        credits_remaining=amount,
        expires_at=expires_at,
    )

    # Atomic increment with F-expression to avoid lost updates
    CompanyWallet.objects.filter(pk=wallet.pk).update(
        balance_credits=F("balance_credits") + amount,
        updated_at=timezone.now(),
    )
    wallet.refresh_from_db(fields=["balance_credits", "updated_at"])

    WalletTransaction.objects.create(
        company=company,
        txn_type=TxnType.GRANT,
        credits_delta=amount,
        balance_after=wallet.balance_credits,
        reason=note or f"{source} grant",
        meta=meta or {},
    )
    return batch


@transaction.atomic
def spend_credits(company, amount: int, *, reason: str, idempotency_key: str = None, meta: dict | None = None):
    if amount <= 0:
        raise ValueError("spend amount must be positive")

    if idempotency_key:
        existing = (
            WalletTransaction.objects
            .filter(company=company, idempotency_key=idempotency_key, txn_type=TxnType.DEBIT)
            .first()
        )
        if existing:
            return existing

    now = timezone.now()
    batches = (
        CreditBatch.objects
        .select_for_update()
        .filter(company=company)
        .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
        .order_by("expires_at", "id")
    )

    available = sum(b.credits_remaining for b in batches)
    if available < amount:
        raise ValueError(f"INSUFFICIENT_CREDITS:{amount}:{amount - available}")

    to_deduct = amount
    consumed_ids = []
    for b in batches:
        if to_deduct <= 0:
            break
        take = min(b.credits_remaining, to_deduct)
        if take > 0:
            b.credits_remaining = b.credits_remaining - take
            b.save(update_fields=["credits_remaining"])
            to_deduct -= take
            consumed_ids.append(b.id)

    if to_deduct != 0:
        raise RuntimeError("Credit deduction mismatch")

    wallet = _get_or_create_wallet(company, for_update=True)

    # Atomic decrement with F-expression
    CompanyWallet.objects.filter(pk=wallet.pk).update(
        balance_credits=F("balance_credits") - amount,
        updated_at=timezone.now(),
    )
    wallet.refresh_from_db(fields=["balance_credits", "updated_at"])

    txn = WalletTransaction.objects.create(
        company=company,
        txn_type=TxnType.DEBIT,
        credits_delta=-amount,
        balance_after=wallet.balance_credits,
        reason=reason,
        meta=(meta or {}),
        idempotency_key=idempotency_key,
        consumed_batches=consumed_ids,  # keep it in the dedicated column for queryability
    )
    return txn


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
        "unit_price_paisa": unit,
        "discount_percent": discount_pct,
        "vat_percent": vat_pct,
        "subtotal_paisa": after_disc,
        "total_paisa": total,
    }


def create_order(company, qty: int, method: str) -> Order:
    code = f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}-{str(uuid4())[:8].upper()}"
    totals = _compute_totals(qty)
    return Order.objects.create(
        code=code,
        company=company,
        credits_qty=qty,
        method=method,
        status=OrderStatus.PENDING,
        **totals,
    )


@transaction.atomic
def finalize_paid_order(order: Order, *, provider_ref: str, amount_paisa: int, payload: dict):
    if order.status == OrderStatus.PAID:
        return order
    if int(amount_paisa) != int(order.total_paisa):
        raise ValueError("AMOUNT_MISMATCH")

    order.status = OrderStatus.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at"])

    payment, _ = Payment.objects.get_or_create(order=order, defaults={
        "method": order.method,
        "requested_amount_paisa": order.total_paisa,
    })
    payment.status = PaymentStatus.COMPLETED
    payment.verified_amount_paisa = amount_paisa
    payment.provider_ref = provider_ref
    payment.raw_payload = payload or {}
    payment.verified_at = timezone.now()
    payment.save()

    grant_credits(order.company, order.credits_qty, source=CreditSource.TOPUP, note=f"Order {order.code}")
    return order


def _khalti_base() -> str:
    base = getattr(settings, "KHALTI_BASE_URL", "https://dev.khalti.com/api/v2")
    return base.strip().rstrip("/")


def _khalti_headers() -> dict:
    # Strip to avoid invisible newline/space issues causing 401
    secret = (getattr(settings, "KHALTI_SECRET_KEY", "") or "").strip()
    return {
        "Authorization": f"Key {secret}",
        "Content-Type": "application/json",
    }


def khalti_initiate(order: Order) -> dict:
    url = f"{_khalti_base()}/epayment/initiate/"
    headers = _khalti_headers()
    payload = {
        "return_url": settings.SITE_BASE_URL.rstrip("/") + reverse("membership:khalti_return"),
        "website_url": settings.SITE_BASE_URL.rstrip("/"),
        "amount": int(order.total_paisa),  # paisa
        "purchase_order_id": order.code,
        "purchase_order_name": f"Credits x{order.credits_qty}",
        "customer_info": {
            # Adjust these fields to your CompanyProfile attributes if needed
            "name": f"{getattr(order.company, 'first_name', '')} {getattr(order.company, 'last_name', '')}".strip()
                    or getattr(order.company, "name", "") or "Company",
            "email": getattr(getattr(order.company, "user", None), "email", "") or "",
            "phone": getattr(order.company, "phone", "") or "",
        },
    }

    try:
        # Use json= to avoid subtle encoding issues
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
    except requests.RequestException as e:
        logger.exception("Khalti initiate network error")
        raise RuntimeError(f"KHALTI_INITIATE_NETWORK: {e}") from e

    if resp.status_code != 200:
        logger.error("Khalti initiate failed [%s] %s", resp.status_code, resp.text)
        raise RuntimeError(f"KHALTI_INITIATE_HTTP_{resp.status_code}: {resp.text}")

    data = resp.json() if resp.content else {}
    if not data.get("pidx") or not data.get("payment_url"):
        logger.error("Khalti initiate missing fields: %s", data)
        raise RuntimeError("KHALTI_INITIATE_BAD_RESPONSE")

    Payment.objects.update_or_create(
        order=order,
        defaults={
            "method": PayMethod.KHALTI,
            "status": PaymentStatus.INITIATED,
            "requested_amount_paisa": order.total_paisa,
            "provider_ref": data.get("pidx"),
            "raw_payload": data,
        },
    )
    return data


def khalti_lookup(pidx: str) -> dict:
    url = f"{_khalti_base()}/epayment/lookup/"
    headers = _khalti_headers()
    try:
        resp = requests.post(url, headers=headers, json={"pidx": pidx}, timeout=20)
    except requests.RequestException as e:
        logger.exception("Khalti lookup network error")
        raise RuntimeError(f"KHALTI_LOOKUP_NETWORK: {e}") from e

    if resp.status_code != 200:
        logger.error("Khalti lookup failed [%s] %s", resp.status_code, resp.text)
        raise RuntimeError(f"KHALTI_LOOKUP_HTTP_{resp.status_code}: {resp.text}")

    return resp.json()


# ------------------------
# eSewa Integration
# ------------------------
import base64, hmac, hashlib
from decimal import Decimal

def _esewa_signature(secret_key: str, message: str) -> str:
    digest = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _esewa_sign_request(total_amount: str, transaction_uuid: str, product_code: str, secret_key: str):
    """
    Per eSewa docs: signed_field_names must be exactly:
    total_amount,transaction_uuid,product_code
    """
    sfn = "total_amount,transaction_uuid,product_code"
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    signature = _esewa_signature(secret_key, message)
    return sfn, signature


def esewa_prepare(order, *, success_url: str, failure_url: str):
    """
    Build form data for eSewa redirect.
    Converts order.total_paisa to rupees (string) for signature.
    """
    env = getattr(settings, "ESEWA_ENV", "UAT").upper()
    form_url = getattr(settings, "ESEWA_FORM_URL", "").strip() or (
        "https://epay.esewa.com.np/api/epay/main/v2/form"
        if env == "PROD"
        else "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
    )

    product_code = getattr(settings, "ESEWA_PRODUCT_CODE")
    secret_key = getattr(settings, "ESEWA_SECRET_KEY")

    # convert paisa to rupees
    total_amount = f"{(Decimal(order.total_paisa) / Decimal(100)).normalize()}"
    amount = total_amount
    transaction_uuid = order.code

    signed_field_names, signature = _esewa_sign_request(
        total_amount, transaction_uuid, product_code, secret_key
    )

    Payment.objects.update_or_create(
        order=order,
        defaults={
            "method": PayMethod.ESEWA,
            "status": PaymentStatus.INITIATED,
            "requested_amount_paisa": order.total_paisa,
            "provider_ref": transaction_uuid,
            "raw_payload": {"prepared_at": timezone.now().isoformat(), "env": env},
        },
    )

    fields = {
        "amount": amount,
        "tax_amount": "0",
        "product_service_charge": "0",
        "product_delivery_charge": "0",
        "total_amount": total_amount,
        "transaction_uuid": transaction_uuid,
        "product_code": product_code,
        "success_url": success_url,
        "failure_url": failure_url,
        "signed_field_names": signed_field_names,
        "signature": signature,
    }

    return {"action": form_url, "method": "POST", "fields": fields}


def esewa_handle_success(encoded_body: bytes):
    """
    Decode Base64 JSON, verify signature, finalize order if COMPLETE.
    """
    try:
        payload = json.loads(base64.b64decode(encoded_body.decode("utf-8")).decode("utf-8"))
    except Exception as e:
        raise ValueError("ESEWA_BAD_PAYLOAD") from e

    sfn = payload.get("signed_field_names")
    if not sfn:
        raise ValueError("ESEWA_MISSING_SFN")

    message = ",".join(f"{k}={payload.get(k)}" for k in sfn.split(","))
    expected = _esewa_signature(getattr(settings, "ESEWA_SECRET_KEY"), message)
    if expected != payload.get("signature"):
        raise ValueError("ESEWA_BAD_SIGNATURE")

    status = (payload.get("status") or "").upper()
    txn_uuid = payload.get("transaction_uuid") or ""
    product_code = payload.get("product_code") or ""
    total_amount_rupees = payload.get("total_amount") or "0"
    txn_code = payload.get("transaction_code") or ""

    if not txn_uuid:
        raise ValueError("ESEWA_NO_TXN_UUID")

    try:
        order = Order.objects.select_for_update().get(code=txn_uuid)
    except Order.DoesNotExist:
        raise ValueError("ORDER_NOT_FOUND")

    amount_paisa = int(Decimal(total_amount_rupees) * 100)

    payment, _ = Payment.objects.get_or_create(
        order=order,
        defaults={"method": PayMethod.ESEWA, "requested_amount_paisa": order.total_paisa},
    )
    payment.raw_payload = payload
    payment.provider_txn_id = txn_code or payment.provider_txn_id
    payment.save(update_fields=["raw_payload", "provider_txn_id"])

    if status == "COMPLETE":
        return finalize_paid_order(
            order,
            provider_ref=txn_uuid,
            amount_paisa=amount_paisa,
            payload=payload,
        )

    # Not complete: mark appropriately
    if status in {"PENDING", "AMBIGUOUS"}:
        payment.status = PaymentStatus.INITIATED
    else:
        payment.status = PaymentStatus.FAILED
    payment.verified_at = timezone.now()
    payment.save(update_fields=["status", "verified_at"])
    return order


def esewa_handle_failure(request_body: bytes | None = None):
    """Optional logging for failure callback."""
    if request_body:
        try:
            logger.warning("eSewa failure: %s", request_body.decode("utf-8")[:1000])
        except Exception:
            logger.warning("eSewa failure (binary body)")

