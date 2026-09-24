from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from candidate.models import Profile
from company.models import CompanyProfile, JobPost
from applications.models import Application, Interview


class InterviewWorkflowTests(TestCase):
    def setUp(self):
        # Create users
        self.candidate_user = User.objects.create_user(
            username="candidate1",
            email="candidate1@test.com",
            password="password123",
            role=User.ROLE_CANDIDATE,
            first_name="John",
            last_name="Doe",
            is_onboarded=True
        )
        self.candidate_profile = Profile.objects.get(user=self.candidate_user)
        self.candidate_profile.first_name = "John"
        self.candidate_profile.last_name = "Doe"
        self.candidate_profile.designation = "Software Engineer"
        self.candidate_profile.email = "candidate1@test.com"
        self.candidate_profile.save()

        self.company_user = User.objects.create_user(
            username="company1",
            email="company1@test.com",
            password="password123",
            role=User.ROLE_COMPANY,
            first_name="Acme",
            last_name="Corp",
            is_onboarded=True
        )
        self.company_profile = CompanyProfile.objects.create(
            user=self.company_user,
            first_name="Acme",
            last_name="Corporation",
            industry="Technology",
            founded_date=timezone.localdate(),
            company_size="10-50",
            about_company="Tech firm",
            phone="9800000000",
            province="bagmati",
            city="Kathmandu",
            postal_code="44600",
            current_address="Kathmandu"
        )

        # Create Job Post
        self.job = JobPost.objects.create(
            company=self.company_profile,
            title="Senior Python Engineer",
            province="bagmati",
            city="Kathmandu",
            location_type="Remote",
            sector="Technology",
            job_type="Full Time",
            job_level="Senior",
            experience_required=3,
            experience_unit="Years",
            openings=2,
            salary_min=80000,
            salary_max=120000,
            salary_period="Monthly",
            application_deadline=timezone.localdate() + timedelta(days=30),
            is_active=True
        )

        # Create Application
        self.application = Application.objects.create(
            candidate=self.candidate_profile,
            company=self.company_profile,
            job_post=self.job,
            status="shortlisted"
        )

        self.client = Client()

    def test_interview_model_properties(self):
        scheduled_time = timezone.now() + timedelta(days=2)
        interview = Interview.objects.create(
            application=self.application,
            company=self.company_profile,
            candidate=self.candidate_profile,
            round_name="Technical Round 1",
            scheduled_at=scheduled_time,
            duration_minutes=45,
            meeting_link="https://meet.google.com/abc-def-ghi"
        )

        self.assertTrue(interview.is_upcoming)
        self.assertEqual(interview.end_time, scheduled_time + timedelta(minutes=45))
        self.assertIn("calendar.google.com", interview.google_calendar_url)
        self.assertIn("Technical+Round+1", interview.google_calendar_url)

        # Check ICS generation
        ics = interview.generate_ics()
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("BEGIN:VEVENT", ics)
        self.assertIn("Technical Round 1", ics)
        self.assertIn("END:VCALENDAR", ics)

    def test_schedule_interview_view(self):
        self.client.login(username="company1", password="password123")
        scheduled_time = (timezone.now() + timedelta(days=3)).strftime("%Y-%m-%dT14:00")

        url = reverse("applications:schedule_interview", kwargs={"app_id": self.application.id})
        response = self.client.post(url, {
            "round_name": "System Design Round",
            "interview_type": "video",
            "scheduled_at": scheduled_time,
            "duration_minutes": "60",
            "meeting_link": "https://meet.google.com/xyz-123",
            "interviewer_name": "Lead Architect",
            "instructions": "Be prepared to discuss microservices architecture."
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        # Check that Interview was created
        interview = Interview.objects.filter(application=self.application).first()
        self.assertIsNotNone(interview)
        self.assertEqual(interview.round_name, "System Design Round")
        self.assertEqual(interview.duration_minutes, 60)

        # Check that Application status synced to 'interview'
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "interview")

    def test_candidate_rsvp_confirm_and_reschedule(self):
        scheduled_time = timezone.now() + timedelta(days=2)
        interview = Interview.objects.create(
            application=self.application,
            company=self.company_profile,
            candidate=self.candidate_profile,
            round_name="HR Screening",
            scheduled_at=scheduled_time,
            duration_minutes=30
        )

        self.client.login(username="candidate1", password="password123")

        # Test Confirm
        rsvp_url = reverse("applications:interview_rsvp", kwargs={"pk": interview.id})
        response = self.client.post(rsvp_url, {
            "action": "confirm",
            "notes": "Looking forward to it!"
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.status_code, 200)
        interview.refresh_from_db()
        self.assertEqual(interview.status, "confirmed")
        self.assertEqual(interview.candidate_notes, "Looking forward to it!")

        # Test Reschedule
        response = self.client.post(rsvp_url, {
            "action": "reschedule",
            "notes": "Can we move this to Friday morning?"
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.status_code, 200)
        interview.refresh_from_db()
        self.assertEqual(interview.status, "reschedule_requested")
        self.assertEqual(interview.candidate_notes, "Can we move this to Friday morning?")

    def test_interview_ics_download(self):
        scheduled_time = timezone.now() + timedelta(days=1)
        interview = Interview.objects.create(
            application=self.application,
            company=self.company_profile,
            candidate=self.candidate_profile,
            round_name="Cultural Fit",
            scheduled_at=scheduled_time,
            duration_minutes=30
        )

        self.client.login(username="candidate1", password="password123")
        ics_url = reverse("applications:interview_ics", kwargs={"pk": interview.id})
        response = self.client.get(ics_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/calendar; charset=utf-8")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        self.assertIn(b"BEGIN:VCALENDAR", response.content)

    def test_candidate_and_company_interview_pages(self):
        scheduled_time = timezone.now() + timedelta(days=2)
        Interview.objects.create(
            application=self.application,
            company=self.company_profile,
            candidate=self.candidate_profile,
            round_name="Final Interview",
            scheduled_at=scheduled_time,
            duration_minutes=45
        )

        # Candidate interviews page
        self.client.login(username="candidate1", password="password123")
        response = self.client.get(reverse("candidate:interviews"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Final Interview")
        self.assertContains(response, "Acme Corporation")

        # Company interviews page
        self.client.login(username="company1", password="password123")
        response = self.client.get(reverse("company:interviews"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Final Interview")
        self.assertContains(response, "John Doe")
