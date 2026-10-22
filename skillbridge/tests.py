from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache

User = get_user_model()


class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="candidate@example.com",
            email="candidate@example.com",
            password="testpassword123",
            role="candidate",
        )

    def tearDown(self):
        cache.clear()

    @override_settings(
        RATELIMIT_ENABLE=True,
        RATELIMIT_RATES={"check_email": "3/m"},
    )
    def test_check_email_rate_limit_json_response(self):
        url = reverse("accounts:check_email_exists") + "?email=candidate@example.com"

        # First 3 requests should succeed
        for _ in range(3):
            response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("exists"), True)

        # 4th request should be rate-limited with HTTP 429
        response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 429)
        data = response.json()
        self.assertEqual(data.get("ok"), False)
        self.assertEqual(data.get("status"), "rate_limited")
        self.assertIn("error", data)

    @override_settings(
        RATELIMIT_ENABLE=False,
        RATELIMIT_RATES={"check_email": "2/m"},
    )
    def test_ratelimit_disabled_setting(self):
        url = reverse("accounts:check_email_exists") + "?email=candidate@example.com"

        # When RATELIMIT_ENABLE is False, quota is not enforced
        for _ in range(5):
            response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
            self.assertEqual(response.status_code, 200)

    @override_settings(
        RATELIMIT_ENABLE=True,
        RATELIMIT_RATES={"login": "2/m"},
    )
    def test_login_rate_limit_html_redirect(self):
        login_url = reverse("accounts:login")

        # 2 attempts
        for _ in range(2):
            self.client.post(login_url, {
                "username": "wrong@example.com",
                "password": "wrongpassword",
            })

        # 3rd attempt should be throttled
        response = self.client.post(
            login_url,
            {
                "username": "wrong@example.com",
                "password": "wrongpassword",
            },
            HTTP_REFERER=login_url,
        )
        # Should redirect back with message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, login_url)
