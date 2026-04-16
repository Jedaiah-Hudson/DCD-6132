from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import CapabilityProfile, User
from core.models import Opportunity
from contracts.models import Contract


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


class OpportunityApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='matcher@example.com',
            password='StrongPass123!',
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

        Contract.objects.create(
            source='procurement',
            title='Cybersecurity Support Services',
            summary='Cyber operations and compliance support.',
            naics_code='541330',
            agency='DoD',
            status='Reviewing',
            partner_name='Northwind Systems',
        )
        Contract.objects.create(
            source='procurement',
            title='Facilities Maintenance',
            summary='General building maintenance support.',
            naics_code='561210',
            agency='GSA',
            status='Submitted',
            partner_name='Atlas Facilities',
        )
        Contract.objects.create(
            source='procurement',
            title='Cloud Engineering Contract',
            summary='Secure cloud migration for federal systems.',
            naics_code='541330',
            agency='VA',
            status='Drafting',
            partner_name='Skyline Tech',
        )

    def test_list_all_opportunities(self):
        response = self.client.get('/api/opportunities/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

    def test_filter_by_naics_code(self):
        response = self.client.get('/api/opportunities/?naics_code=541330')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(all(item['naics_code'] == '541330' for item in response.data))

    def test_dashboard_fields_are_present_in_opportunity_payload(self):
        response = self.client.get('/api/opportunities/?naics_code=541330')

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertIn('title', response.data[0])
        self.assertIn('description', response.data[0])
        self.assertIn('naics_code', response.data[0])
        self.assertIn('agency', response.data[0])
        self.assertIn('status', response.data[0])
        self.assertIn('partner', response.data[0])

    def test_search_by_keyword(self):
        response = self.client.get('/api/opportunities/?search=cloud')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Cloud Engineering Contract')

    def test_apply_naics_and_search_together(self):
        response = self.client.get('/api/opportunities/?naics_code=541330&search=cyber')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Cybersecurity Support Services')

    def test_filter_by_agency_case_insensitive(self):
        response = self.client.get('/api/opportunities/?agency=dod')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['agency'], 'DoD')

    def test_filter_by_status_case_insensitive(self):
        response = self.client.get('/api/opportunities/?status=submitted')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'Submitted')

    def test_apply_all_filters_together(self):
        response = self.client.get('/api/opportunities/?search=cloud&naics_code=541330&agency=va&status=drafting')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Cloud Engineering Contract')

    def test_search_matches_partner_name(self):
        response = self.client.get('/api/opportunities/?search=northwind')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['partner'], 'Northwind Systems')

    def test_match_user_filters_by_capability_profile_naics_codes(self):
        CapabilityProfile.objects.create(
            user=self.user,
            company_name='Match Co',
            naics_codes='541330, 123456',
        )

        response = self.client.get('/api/opportunities/?match_user=true', **self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(all(item['naics_code'] == '541330' for item in response.data))

    def test_match_user_requires_authentication(self):
        response = self.client.get('/api/opportunities/?match_user=true')

        self.assertEqual(response.status_code, 401)

    def test_opportunity_api_ignores_legacy_core_opportunity_rows(self):
        Opportunity.objects.create(
            title='Legacy Opportunity Row',
            description='This should not appear in the active API.',
            naics_code='999999',
            agency='Legacy Agency',
            status='Legacy',
        )

        response = self.client.get('/api/opportunities/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertFalse(any(item['title'] == 'Legacy Opportunity Row' for item in response.data))
