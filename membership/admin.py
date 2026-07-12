# membership/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import CompanyWallet, CreditBatch, WalletTransaction, Order, Payment, PaymentStatus, OrderStatus
from .services import finalize_paid_order


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
    list_display = ("order", "method", "status", "display_receipt", "verified_amount_paisa", "provider_ref", "provider_txn_id", "verified_at")
    list_filter = ("method", "status")
    search_fields = ("order__code", "provider_ref", "provider_txn_id")
    raw_id_fields = ("order",)
    list_select_related = ("order",)
    readonly_fields = ("display_receipt",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ["approve_payments", "reject_payments"]

    def display_receipt(self, obj):
        if obj.receipt:
            return format_html('<a href="{}" target="_blank">View Receipt</a>', obj.receipt.url)
        return "No Receipt"
    display_receipt.short_description = "Receipt File"

    @admin.action(description="Approve selected payments (Grant credits)")
    def approve_payments(self, request, queryset):
        count = 0
        for payment in queryset:
            if payment.status in (PaymentStatus.INITIATED, PaymentStatus.PENDING_VERIFICATION):
                finalize_paid_order(
                    payment.order,
                    provider_ref=f"MANUAL_{request.user.username}",
                    amount_paisa=payment.requested_amount_paisa,
                    payload={"verified_by": request.user.username}
                )
                count += 1
        self.message_user(request, f"Successfully approved {count} payment(s). Credits granted.", messages.SUCCESS)

    @admin.action(description="Reject selected payments (Cancel order)")
    def reject_payments(self, request, queryset):
        count = 0
        for payment in queryset:
            if payment.status in (PaymentStatus.INITIATED, PaymentStatus.PENDING_VERIFICATION):
                payment.status = PaymentStatus.FAILED
                payment.save(update_fields=["status"])
                
                order = payment.order
                order.status = OrderStatus.FAILED
                order.save(update_fields=["status"])
                
                count += 1
        self.message_user(request, f"Successfully rejected {count} payment(s).", messages.WARNING)
