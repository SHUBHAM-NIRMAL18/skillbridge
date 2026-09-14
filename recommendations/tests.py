from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from candidate.models import Profile, Experience, Project
from company.models import CompanyProfile, JobPost, InternshipPost
from applications.models import Application
from recommendations.models import CandidateEvent
from recommendations.simple_hybrid import (
    _skill_similarity,
    _candidate_aggregated_skills,
    recommend_all_for_candidate,
    compute_candidate_job_fit,
    get_similar_jobs,
    invalidate_candidate_rec_cache,
)

User = get_user_model()

class RecommendationEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="candidate1",
            email="cand1@example.com",
            password="password123",
            role="candidate"
        )
        self.profile = self.user.profile
        self.profile.first_name = "Alice"
        self.profile.last_name = "Smith"
        self.profile.designation = "Full Stack Developer"
        self.profile.skills = "python, django, react"
        self.profile.city = "Kathmandu"
        self.profile.province = "3"
        self.profile.save()

        self.company_user = User.objects.create_user(
            username="company1",
            email="hr@techcorp.com",
            password="password123",
            role="company"
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user,
            first_name="TechCorp",
            last_name="Nepal",
            industry="IT",
            founded_date="2020-01-01",
            company_size="11-50",
            about_company="Tech firm",
            phone="9800000000",
            province="Bagmati",
            city="Kathmandu",
            postal_code="44600",
            current_address="Thamel"
        )

        today = timezone.localdate()
        self.job1 = JobPost.objects.create(
            company=self.company,
            title="Backend Python Developer",
            province="Bagmati",
            city="Kathmandu",
            location_type="Remote",
            sector="Technology",
            application_deadline=today + timezone.timedelta(days=14),
            job_type="Full Time",
            job_level="Mid",
            experience_required=2,
            experience_unit="Years",
            openings=2,
            salary_min=50000,
            salary_max=80000,
            salary_period="Monthly",
            is_active=True
        )
        self.job1.skills.add("python", "django", "postgresql")

        self.job2 = JobPost.objects.create(
            company=self.company,
            title="Frontend React Specialist",
            province="Bagmati",
            city="Kathmandu",
            location_type="Hybrid",
            sector="Technology",
            application_deadline=today + timezone.timedelta(days=14),
            job_type="Full Time",
            job_level="Mid",
            experience_required=1,
            experience_unit="Years",
            openings=1,
            salary_min=40000,
            salary_max=60000,
            salary_period="Monthly",
            is_active=True
        )
        self.job2.skills.add("react", "javascript", "css3")

    def test_skill_similarity_soft_matching(self):
        # Candidate has "django" and "python", job requires "django", "python", "sql"
        # django relates to sql in SKILL_RELATIONS, so candidate should get partial credit for sql
        cand_skills = ["python", "django"]
        job_skills = ["python", "django", "sql"]
        sim, matched, missing = _skill_similarity(cand_skills, job_skills)
        self.assertIn("django", matched)
        self.assertIn("python", matched)
        self.assertIn("sql", missing)
        self.assertGreater(sim, 0.6)

    def test_candidate_aggregated_skills(self):
        # Add a project with extra technologies
        Project.objects.create(
            profile=self.profile,
            title="Dockerized App",
            description="App container",
            technologies="docker, k8s, redis",
            project_url="https://github.com/alice/project"
        )
        agg_skills = _candidate_aggregated_skills(self.profile)
        self.assertIn("python", agg_skills)
        self.assertIn("django", agg_skills)
        self.assertIn("docker", agg_skills)
        self.assertIn("kubernetes", agg_skills)
        self.assertIn("redis", agg_skills)

    def test_negative_filtering_applied_job(self):
        # Candidate applies to job1
        Application.objects.create(
            candidate=self.profile,
            company=self.company,
            job_post=self.job1,
            status="applied"
        )
        recs = recommend_all_for_candidate(self.user, use_cache=False)
        rec_job_ids = [r.obj_id for r in recs if not r.is_internship]
        self.assertNotIn(self.job1.id, rec_job_ids)

    def test_negative_filtering_dismissed_job(self):
        # Candidate dismisses job2
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(JobPost)
        CandidateEvent.objects.create(
            user=self.user,
            item_content_type=ct,
            item_object_id=self.job2.id,
            event_type="dismiss"
        )
        recs = recommend_all_for_candidate(self.user, use_cache=False)
        rec_job_ids = [r.obj_id for r in recs if not r.is_internship]
        self.assertNotIn(self.job2.id, rec_job_ids)

    def test_compute_candidate_job_fit(self):
        fit = compute_candidate_job_fit(self.profile, self.job1)
        self.assertGreater(fit.score, 0.5)
        self.assertIn("python", fit.matched_skills)
        self.assertIn("django", fit.matched_skills)

    def test_get_similar_jobs(self):
        similar = get_similar_jobs(self.job1, limit=3)
        self.assertIsInstance(similar, list)

