from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class ProfileAccessTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login-vis/'))

    def test_notifications_requires_login(self):
        response = self.client.get(reverse('notifications'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login-vis/'))

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login-vis/'))

    def test_profile_loads_for_authenticated_user(self):
        user = User.objects.create_user(
            email='profileuser@example.com',
            password='StrongPass123!',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_exposes_signup_for_anonymous_user(self):
        response = self.client.get('/accounts/login-vis/')
        self.assertContains(response, 'Sign Up')
        self.assertNotContains(response, 'Profile')

    def test_nav_shows_profile_and_logout_for_authenticated_user(self):
        user = User.objects.create_user(
            email='navuser@example.com',
            password='StrongPass123!',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Profile')
        self.assertContains(response, 'Logout')
        self.assertNotContains(response, 'Sign Up')
