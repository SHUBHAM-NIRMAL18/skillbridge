from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from company.models import CompanyProfile
from membership.models import Order, Payment, PaymentStatus, OrderStatus, PayMethod, CompanyWallet
from datetime import date
from django.contrib.admin.sites import AdminSite

User = get_user_model()

class BankPaymentReceiptTests(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username="testcompany",
            email="testcompany@example.com",
            password="Password123!",
            role="company"
        )
        # Create company profile
        self.company = CompanyProfile.objects.create(
            user=self.user,
            first_name="Test Company",
            last_name="Ltd",
            industry="IT",
            founded_date=date(2020, 1, 1),
            company_size="1-10",
            about_company="About",
            phone="9876543210",
            province="Bagmati",
            city="Kathmandu",
            postal_code="44600",
            current_address="KTM"
        )
        # Get the automatically created wallet and reset credits for clean testing
        self.wallet = CompanyWallet.objects.get(company=self.company)
        self.wallet.balance_credits = 0
        self.wallet.save()
        
        # Create order
        self.order = Order.objects.create(
            code="ORD-TEST-123",
            company=self.company,
            credits_qty=100,
            unit_price_paisa=1000,
            discount_percent=0,
            vat_percent=13,
            subtotal_paisa=100000,
            total_paisa=113000,
            method=PayMethod.BANK,
            status=OrderStatus.PENDING
        )

    def test_bank_order_view_get(self):
        self.client.login(username="testcompany", password="Password123!")
        response = self.client.get(reverse("membership:bank_order", args=[self.order.code]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ORD-TEST-123")
        self.assertContains(response, "Rs 1,130")

    def test_upload_receipt_via_post(self):
        self.client.login(username="testcompany", password="Password123!")
        
        # Generate dummy file
        dummy_file = SimpleUploadedFile(
            "receipt.jpg",
            b"dummy_image_content",
            content_type="image/jpeg"
        )
        
        # Upload receipt
        response = self.client.post(
            reverse("membership:bank_order", args=[self.order.code]),
            {"receipt": dummy_file}
        )
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        
        # Verify payment status
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.status, PaymentStatus.PENDING_VERIFICATION)
        self.assertIsNotNone(payment.receipt)

    def test_admin_approve_action(self):
        # Create payment record that is pending verification
        payment = Payment.objects.create(
            order=self.order,
            method=PayMethod.BANK,
            status=PaymentStatus.PENDING_VERIFICATION,
            requested_amount_paisa=self.order.total_paisa,
        )
        
        # Call admin action programmatically
        from membership.admin import PaymentAdmin
        # Setup mock admin request
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        # Make superuser
        admin_user = User.objects.create_superuser("admin", "admin@example.com", "AdminPass123!")
        request = MockRequest(admin_user)
        
        admin_instance = PaymentAdmin(Payment, AdminSite())
        # Mock message_user to prevent session middleware configuration errors
        admin_instance.message_user = lambda request, message, level=None: None
        
        admin_instance.approve_payments(request, Payment.objects.filter(pk=payment.pk))
        
        # Refresh from DB
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.wallet.refresh_from_db()
        
        # Verify completed status and credits granted
        self.assertEqual(payment.status, PaymentStatus.COMPLETED)
        self.assertEqual(self.order.status, OrderStatus.PAID)
        self.assertEqual(self.wallet.balance_credits, 100)
