from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from company.models import CompanyProfile, JobPost
from candidate.models import Profile
from applications.models import Application

User = get_user_model()

class CompanyApplicantsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company_user = User.objects.create_user(
            username="company_boss",
            email="boss@company.com",
            password="secretpassword",
            role="company"
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user,
            first_name="Acme",
            last_name="Corp",
            industry="Software",
            founded_date="2021-01-01",
            company_size="11-50",
            about_company="Best software",
            phone="9811111111",
            province="Bagmati",
            city="Kathmandu",
            postal_code="44600",
            current_address="Lazimpat"
        )

        today = timezone.localdate()
        self.job = JobPost.objects.create(
            company=self.company,
            title="Senior Python Backend Engineer",
            province="Bagmati",
            city="Kathmandu",
            location_type="Remote",
            sector="Technology",
            application_deadline=today + timezone.timedelta(days=20),
            job_type="Full Time",
            job_level="Senior",
            experience_required=3,
            experience_unit="Years",
            openings=1,
            salary_min=80000,
            salary_max=120000,
            salary_period="Monthly",
            is_active=True
        )
        self.job.skills.add("python", "django", "postgresql")

        # Candidate 1: strong match
        self.cand_user1 = User.objects.create_user(username="cand1", email="c1@test.com", password="pwd", role="candidate")
        self.prof1 = self.cand_user1.profile
        self.prof1.first_name = "Dev"
        self.prof1.last_name = "One"
        self.prof1.skills = "python, django, postgresql"
        self.prof1.designation = "Senior Python Developer"
        self.prof1.save()

        # Candidate 2: weak match
        self.cand_user2 = User.objects.create_user(username="cand2", email="c2@test.com", password="pwd", role="candidate")
        self.prof2 = self.cand_user2.profile
        self.prof2.first_name = "Dev"
        self.prof2.last_name = "Two"
        self.prof2.skills = "graphic design, photoshop"
        self.prof2.designation = "UI Designer"
        self.prof2.save()

        # Create applications for both
        self.app1 = Application.objects.create(candidate=self.prof1, company=self.company, job_post=self.job, status="applied")
        self.app2 = Application.objects.create(candidate=self.prof2, company=self.company, job_post=self.job, status="applied")

    def test_applicants_list_fit_score_and_best_match_sort(self):
        self.client.login(username="company_boss", password="secretpassword")
        url = reverse("company:job_applicants", kwargs={"pk": self.job.id})
        
        # Test default load
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        apps = res.context["apps"]
        self.assertEqual(len(apps), 2)
        # Check that match_score was computed on applications
        scores = {a.id: a.match_score for a in apps}
        self.assertGreater(scores[self.app1.id], scores[self.app2.id])

        # Test sorting by best_match
        res_sorted = self.client.get(url + "?sort=best_match")
        self.assertEqual(res_sorted.status_code, 200)
        sorted_apps = res_sorted.context["apps"]
        # Candidate 1 should be first because of higher match score
        self.assertEqual(sorted_apps[0].id, self.app1.id)
        self.assertEqual(sorted_apps[1].id, self.app2.id)

