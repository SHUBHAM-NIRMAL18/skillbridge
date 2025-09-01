from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from company.models import CompanyProfile
from .models import CompanyWallet, CreditSource
from .services import grant_credits

@receiver(post_save, sender=CompanyProfile)
def on_company_created(sender, instance: CompanyProfile, created, **kwargs):
    if not created:
        return
    CompanyWallet.objects.get_or_create(company=instance)
    grant_credits(
        company=instance,
        amount=getattr(settings, "CREDITS_SIGNUP_BONUS", 50),
        source=CreditSource.SIGNUP_BONUS,
        note="Welcome credits",
        expires_in_days=getattr(settings, "CREDIT_BONUS_EXPIRY_DAYS", 90),
        meta={"reason": "new_company"},
    )
