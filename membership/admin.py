# membership/admin.py
from django.contrib import admin
from .models import CompanyWallet, CreditBatch, WalletTransaction, Order, Payment


@admin.register(CompanyWallet)
class CompanyWalletAdmin(admin.ModelAdmin):
    list_display = ("company", "balance_credits", "updated_at")
    search_fields = ("company__user__email", "company__first_name", "company__last_name")
    raw_id_fields = ("company",)
    list_select_related = ("company",)
    ordering = ("-updated_at",)


@admin.register(CreditBatch)
class CreditBatchAdmin(admin.ModelAdmin):
    list_display = ("company", "source", "credits_total", "credits_remaining", "expires_at", "created_at")
    list_filter = ("source",)
    search_fields = ("company__user__email",)
    raw_id_fields = ("company",)
    list_select_related = ("company",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("company", "txn_type", "credits_delta", "balance_after", "reason", "idempotency_key", "created_at")
    list_filter = ("txn_type",)
    search_fields = ("idempotency_key", "reason", "company__user__email")
    raw_id_fields = ("company",)
    list_select_related = ("company",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("code", "company", "credits_qty", "total_paisa", "method", "status", "created_at", "paid_at")
    list_filter = ("status", "method")
    search_fields = ("code", "company__user__email")
    raw_id_fields = ("company",)
    list_select_related = ("company",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "method", "status", "verified_amount_paisa", "provider_ref", "provider_txn_id", "verified_at")
    list_filter = ("method", "status")
    search_fields = ("order__code", "provider_ref", "provider_txn_id")
    raw_id_fields = ("order",)
    list_select_related = ("order",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
