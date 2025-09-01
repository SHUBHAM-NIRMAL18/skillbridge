from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone

COMPANY_MODEL = "company.CompanyProfile"

class CreditSource(models.TextChoices):
    SIGNUP_BONUS = "SIGNUP_BONUS", "Signup Bonus"
    TOPUP        = "TOPUP",        "Top-up"
    PLAN         = "PLAN",         "Plan"
    ADJUSTMENT   = "ADJUSTMENT",   "Admin Adjustment"

class TxnType(models.TextChoices):
    GRANT  = "GRANT",  "Grant"
    DEBIT  = "DEBIT",  "Debit"
    REFUND = "REFUND", "Refund"

class CompanyWallet(models.Model):
    company = models.OneToOneField(COMPANY_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance_credits = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet({self.company_id})={self.balance_credits}"

class CreditBatch(models.Model):
    company = models.ForeignKey(COMPANY_MODEL, on_delete=models.CASCADE, related_name="credit_batches")
    source = models.CharField(max_length=32, choices=CreditSource.choices)
    credits_total = models.IntegerField()
    credits_remaining = models.IntegerField()
    # None => non-expiring (use this for purchased credits)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["company", "expires_at"])]

    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()

class WalletTransaction(models.Model):
    company = models.ForeignKey(COMPANY_MODEL, on_delete=models.CASCADE, related_name="wallet_transactions")
    txn_type = models.CharField(max_length=16, choices=TxnType.choices)
    credits_delta = models.IntegerField()            # + for grant/refund, - for debit
    balance_after = models.IntegerField()
    reason = models.CharField(max_length=64, blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=128, unique=True, null=True, blank=True)
    consumed_batches = models.JSONField(default=list, blank=True)   # [batch_id, ...] for debits
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

# ——— Orders & Payments shell (for Buy Credits flow) ———
class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PAID    = "PAID",    "Paid"
    FAILED  = "FAILED",  "Failed"
    CANCELED= "CANCELED","Canceled"

class PayMethod(models.TextChoices):
    KHALTI = "KHALTI", "Khalti"
    ESEWA  = "ESEWA",  "eSewa"
    BANK   = "BANK",   "Bank Transfer"
    QR     = "QR",     "QR Payment"

class Order(models.Model):
    code = models.CharField(max_length=40, unique=True)  # e.g., "ORD-20250902-ABC123"
    company = models.ForeignKey(COMPANY_MODEL, on_delete=models.CASCADE, related_name="orders")
    credits_qty = models.IntegerField()
    unit_price_paisa = models.IntegerField()       # store money in minor units
    discount_percent = models.IntegerField(default=0)
    vat_percent = models.IntegerField(default=13)
    subtotal_paisa = models.IntegerField()
    total_paisa = models.IntegerField()
    method = models.CharField(max_length=10, choices=PayMethod.choices)
    status = models.CharField(max_length=10, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

class PaymentStatus(models.TextChoices):
    INITIATED = "INITIATED", "Initiated"
    COMPLETED = "COMPLETED", "Completed"
    FAILED    = "FAILED",    "Failed"

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    method = models.CharField(max_length=10, choices=PayMethod.choices)
    status = models.CharField(max_length=12, choices=PaymentStatus.choices, default=PaymentStatus.INITIATED)
    requested_amount_paisa = models.IntegerField()
    verified_amount_paisa = models.IntegerField(null=True, blank=True)
    provider_ref = models.CharField(max_length=80, null=True, blank=True)  # Khalti pidx / eSewa txn uuid
    provider_txn_id = models.CharField(max_length=80, null=True, blank=True)  # e.g., eSewa refId
    raw_payload = models.JSONField(default=dict, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
