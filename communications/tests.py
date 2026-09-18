from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from candidate.models import Profile
from company.models import CompanyProfile, JobPost
from applications.models import Application
from communications.models import Notification, Conversation, Message
from communications.services import notify_user, get_or_create_conversation, send_conversation_message


class CommunicationsModelAndServiceTests(TestCase):
    def setUp(self):
        # Candidate User (signal automatically creates self.cand_user.profile)
        self.cand_user = User.objects.create_user(
            username="candidate1",
            email="cand1@test.com",
            password="password123",
            role="candidate"
        )
        self.cand_profile = self.cand_user.profile
        self.cand_profile.first_name = "Aarav"
        self.cand_profile.last_name = "Sharma"
        self.cand_profile.email = "cand1@test.com"
        self.cand_profile.designation = "Python Developer"
        self.cand_profile.resume = SimpleUploadedFile("resume.pdf", b"%PDF-1.4 dummy pdf content", content_type="application/pdf")
        self.cand_profile.save()

        # Company User & Profile
        self.comp_user = User.objects.create_user(
            username="company1",
            email="comp1@test.com",
            password="password123",
            role="company"
        )
        self.comp_profile = CompanyProfile.objects.create(
            user=self.comp_user,
            first_name="TechCorp",
            last_name="Nepal",
            industry="IT",
            founded_date=timezone.now().date(),
            company_size="11-50",
            about_company="Leading tech firm.",
            phone="9800000000",
            province="Bagmati",
            city="Kathmandu",
            postal_code="44600",
            current_address="New Baneshwor"
        )

        # Job Post & Application
        self.job = JobPost.objects.create(
            company=self.comp_profile,
            title="Backend Engineer",
            province="Bagmati",
            city="Kathmandu",
            location_type="Onsite",
            sector="Technology",
            application_deadline=timezone.now().date() + timedelta(days=30),
            job_type="Full Time",
            job_level="Mid",
            experience_required=2,
            experience_unit="Years",
            openings=2,
            salary_min=50000,
            salary_max=80000,
            salary_period="Monthly"
        )
        self.app = Application.objects.create(
            candidate=self.cand_profile,
            company=self.comp_profile,
            job_post=self.job,
            resume_file=SimpleUploadedFile("app_resume.pdf", b"%PDF-1.4 application resume content", content_type="application/pdf"),
            status="applied"
        )

    def test_notification_creation_and_mark_read(self):
        notif = notify_user(
            recipient=self.cand_user,
            title="Test Alert",
            message="Your application was shortlisted.",
            action_url="/candidate/applications/",
            sender=self.comp_user,
            notification_type="application_status"
        )
        self.assertIsNotNone(notif)
        self.assertFalse(notif.is_read)
        self.assertEqual(Notification.objects.filter(recipient=self.cand_user, is_read=False).count(), 1)

        # Mark read via view
        client = Client()
        client.login(username="candidate1", password="password123")
        response = client.get(reverse("communications:mark_notification_read", args=[notif.id]))
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        self.assertRedirects(response, "/candidate/applications/", fetch_redirect_response=False)

    def test_conversation_and_messaging_flow(self):
        convo, created = get_or_create_conversation(
            candidate=self.cand_profile,
            company=self.comp_profile,
            application=self.app
        )
        self.assertTrue(created)
        self.assertEqual(convo.candidate, self.cand_profile)
        self.assertEqual(convo.company, self.comp_profile)

        # Candidate sends message
        msg1 = send_conversation_message(convo, self.cand_user, "Hello, I am excited about this role!")
        self.assertEqual(convo.messages.count(), 1)
        self.assertEqual(convo.unread_count_for_user(self.comp_user), 1)
        self.assertEqual(convo.unread_count_for_user(self.cand_user), 0)

        # Verify notification was sent to company
        comp_notif = Notification.objects.filter(recipient=self.comp_user).first()
        self.assertIsNotNone(comp_notif)
        self.assertEqual(comp_notif.notification_type, "new_message")

        # Company replies
        msg2 = send_conversation_message(convo, self.comp_user, "Thanks for applying Aarav, when are you free for a call?")
        self.assertEqual(convo.messages.count(), 2)
        self.assertEqual(convo.unread_count_for_user(self.cand_user), 1)

        # Candidate notification
        cand_notif = Notification.objects.filter(recipient=self.cand_user, notification_type="new_message").first()
        self.assertIsNotNone(cand_notif)

    def test_send_message_api(self):
        convo, _ = get_or_create_conversation(self.cand_profile, self.comp_profile)
        client = Client()
        client.login(username="candidate1", password="password123")

        url = reverse("communications:send_message_api", args=[convo.id])
        response = client.post(
            url,
            {"text": "Checking in via AJAX API"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data["message"]["text"], "Checking in via AJAX API")
        self.assertEqual(convo.messages.count(), 1)


class ProtectedResumeSecurityTests(TestCase):
    def setUp(self):
        self.cand_user = User.objects.create_user(
            username="candidate1",
            email="cand1@test.com",
            password="password123",
            role="candidate"
        )
        self.cand_profile = self.cand_user.profile
        self.cand_profile.first_name = "Aarav"
        self.cand_profile.last_name = "Sharma"
        self.cand_profile.email = "cand1@test.com"
        self.cand_profile.resume = SimpleUploadedFile("my_cv.pdf", b"%PDF-1.4 candidate cv", content_type="application/pdf")
        self.cand_profile.save()

        self.comp_user = User.objects.create_user(
            username="company1",
            email="comp1@test.com",
            password="password123",
            role="company"
        )
        self.comp_profile = CompanyProfile.objects.create(
            user=self.comp_user,
            first_name="TechCorp",
            last_name="Nepal",
            industry="IT",
            founded_date=timezone.now().date(),
            company_size="11-50",
            phone="9800000000",
            province="Bagmati",
            city="Kathmandu"
        )

        self.job = JobPost.objects.create(
            company=self.comp_profile,
            title="Backend Engineer",
            province="Bagmati",
            city="Kathmandu",
            location_type="Onsite",
            sector="Technology",
            application_deadline=timezone.now().date() + timedelta(days=30),
            job_type="Full Time",
            job_level="Mid",
            experience_required=2,
            experience_unit="Years",
            openings=2,
            salary_min=50000,
            salary_max=80000,
            salary_period="Monthly"
        )
        self.app = Application.objects.create(
            candidate=self.cand_profile,
            company=self.comp_profile,
            job_post=self.job,
            resume_file=SimpleUploadedFile("app_cv.pdf", b"%PDF-1.4 application cv", content_type="application/pdf"),
            status="applied"
        )

        # Unrelated third-party stranger
        self.stranger = User.objects.create_user(
            username="stranger",
            email="stranger@test.com",
            password="password123",
            role="candidate"
        )

    def test_candidate_can_download_own_resume(self):
        client = Client()
        client.login(username="candidate1", password="password123")
        url = reverse("candidate:download_resume", args=[self.cand_profile.id])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("inline", response.headers.get("Content-Disposition", ""))

    def test_hiring_company_can_download_applicant_resume(self):
        client = Client()
        client.login(username="company1", password="password123")
        url = reverse("applications:download_resume", args=[self.app.id])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_unrelated_stranger_is_forbidden(self):
        client = Client()
        client.login(username="stranger", password="password123")

        # Attempt to access candidate profile resume
        cand_url = reverse("candidate:download_resume", args=[self.cand_profile.id])
        resp1 = client.get(cand_url)
        self.assertEqual(resp1.status_code, 403)

        # Attempt to access application resume
        app_url = reverse("applications:download_resume", args=[self.app.id])
        resp2 = client.get(app_url)
        self.assertEqual(resp2.status_code, 403)

    def test_unauthenticated_user_redirected_to_login(self):
        client = Client()
        cand_url = reverse("candidate:download_resume", args=[self.cand_profile.id])
        response = client.get(cand_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
