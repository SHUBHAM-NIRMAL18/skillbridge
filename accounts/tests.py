from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from candidate.models import Profile, Education, SocialLink
from company.models import CompanyProfile

User = get_user_model()


class OnboardingFlowTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_candidate_registration_and_onboarding(self):
        # 1. Candidate Registration redirects to candidate onboarding
        register_url = reverse("accounts:register_candidate")
        data = {
            "username": "new_cand",
            "email": "cand@test.com",
            "password1": "ComplexPass123!",
            "password2": "ComplexPass123!",
        }
        resp = self.client.post(register_url, data, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("candidate:onboarding"), resp.url)

        user = User.objects.get(email="cand@test.com")
        self.assertEqual(user.role, User.ROLE_CANDIDATE)
        self.assertFalse(user.is_onboarded)

        # 2. Candidate Onboarding GET
        onboarding_url = reverse("candidate:onboarding")
        resp_get = self.client.get(onboarding_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, "Tell Us About Yourself")

        # 3. Candidate Onboarding POST
        onboarding_data = {
            "first_name": "Sita",
            "last_name": "Sharma",
            "phone_number": "9841234567",
            "gender": "F",
            "date_of_birth": "1998-05-15",
            "province": "3",
            "city": "Kathmandu",
            "current_address": "Baneshwor",
            "designation": "Frontend Engineer",
            "experience_level": "mid",
            "sectors": "Technology, FinTech",
            "skills": "JavaScript, React, CSS",
            "about_me": "Passionate frontend engineer with 3 years experience.",
            "institution": "Tribhuvan University",
            "degree": "BSc. CSIT",
            "field_of_study": "Computer Science",
            "edu_start_date": "2016-09-01",
            "edu_end_date": "2020-09-01",
            "linkedin_url": "https://linkedin.com/in/sitasharma",
        }
        resp_post = self.client.post(onboarding_url, onboarding_data, follow=False)
        self.assertEqual(resp_post.status_code, 302)
        self.assertIn("step=complete", resp_post.url)

        user.refresh_from_db()
        self.assertTrue(user.is_onboarded)
        self.assertTrue(user.has_completed_onboarding)

        profile = user.profile
        self.assertEqual(profile.first_name, "Sita")
        self.assertEqual(profile.designation, "Frontend Engineer")
        self.assertTrue(Education.objects.filter(profile=profile, institution="Tribhuvan University").exists())
        self.assertTrue(SocialLink.objects.filter(profile=profile, platform="linkedin").exists())

        # 4. Success screen load
        resp_complete = self.client.get(reverse("candidate:onboarding") + "?step=complete")
        self.assertEqual(resp_complete.status_code, 200)
        self.assertContains(resp_complete, "You're All Set, Sita!")

        # 5. Subsequent login redirects to dashboard
        self.client.logout()
        login_resp = self.client.post(reverse("accounts:login"), {
            "username": "cand@test.com",
            "password": "ComplexPass123!",
        }, follow=False)
        self.assertEqual(login_resp.status_code, 302)
        self.assertEqual(login_resp.url, reverse("candidate:dashboard"))

    def test_company_registration_and_onboarding(self):
        # 1. Company Registration redirects to company onboarding
        register_url = reverse("accounts:register_company")
        data = {
            "username": "tech_solutions",
            "email": "hr@techsolutions.com",
            "password1": "ComplexPass123!",
            "password2": "ComplexPass123!",
        }
        resp = self.client.post(register_url, data, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("company:onboarding"), resp.url)

        user = User.objects.get(email="hr@techsolutions.com")
        self.assertEqual(user.role, User.ROLE_COMPANY)
        self.assertFalse(user.is_onboarded)

        # 2. Company accessing dashboard before onboarding is redirected to onboarding
        dash_resp = self.client.get(reverse("company:dashboard"))
        self.assertEqual(dash_resp.status_code, 302)
        self.assertIn(reverse("company:onboarding"), dash_resp.url)

        # 3. Company Onboarding GET
        onboarding_url = reverse("company:onboarding")
        resp_get = self.client.get(onboarding_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, "Company Identity")

        # 4. Company Onboarding POST
        onboarding_data = {
            "first_name": "Tech Solutions",
            "last_name": "Pvt. Ltd.",
            "industry": "Software & IT",
            "company_size": "11-50",
            "founded_date": "2018-04-12",
            "province": "Bagmati",
            "city": "Kathmandu",
            "postal_code": "44600",
            "current_address": "Lazimpat Road",
            "phone": "9812345678",
            "website_url": "https://techsolutions.com",
            "about_company": "Leading software development and cloud consulting company.",
            "social_link": "https://linkedin.com/company/techsolutions",
            "notify_on_application": True,
        }
        resp_post = self.client.post(onboarding_url, onboarding_data, follow=False)
        self.assertEqual(resp_post.status_code, 302)
        self.assertIn("step=complete", resp_post.url)

        user.refresh_from_db()
        self.assertTrue(user.is_onboarded)
        self.assertTrue(user.has_completed_onboarding)

        company_profile = user.company_profile
        self.assertEqual(company_profile.first_name, "Tech Solutions")
        self.assertEqual(company_profile.credits_balance, 50)

        # 5. Success screen load
        resp_complete = self.client.get(reverse("company:onboarding") + "?step=complete")
        self.assertEqual(resp_complete.status_code, 200)
        self.assertContains(resp_complete, "Welcome Aboard, Tech Solutions!")
        self.assertContains(resp_complete, "50 Free Posting Credits Granted!")

        # 6. Subsequent login redirects to dashboard
        self.client.logout()
        login_resp = self.client.post(reverse("accounts:login"), {
            "username": "hr@techsolutions.com",
            "password": "ComplexPass123!",
        }, follow=False)
        self.assertEqual(login_resp.status_code, 302)
        self.assertEqual(login_resp.url, reverse("company:dashboard"))
