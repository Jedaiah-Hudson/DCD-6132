from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from unittest.mock import patch

from accounts.models import AdditionalEmail, User


class LinkedEmailApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='StrongPass123!',
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='StrongPass123!',
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

    def test_add_linked_email_success(self):
        with patch('accounts.views.refresh_contracting_opportunities_for_user') as mock_refresh:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    '/accounts/linked-emails/',
                    {'email': '  NewEmail@Example.com  '},
                    format='json',
                    **self.auth_headers,
                )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'Email added successfully.')
        self.assertTrue(response.data['opportunities_refreshed'])
        self.assertEqual(response.data['email']['email'], 'newemail@example.com')
        self.assertTrue(
            AdditionalEmail.objects.filter(
                user=self.user,
                email='newemail@example.com',
            ).exists()
        )
        mock_refresh.assert_called_once()
        self.assertEqual(mock_refresh.call_args[0][0].id, self.user.id)

    def test_invalid_email_rejected(self):
        response = self.client.post(
            '/accounts/linked-emails/',
            {'email': 'not-an-email'},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid email format.')

    def test_duplicate_email_rejected(self):
        AdditionalEmail.objects.create(user=self.user, email='dup@example.com')

        response = self.client.post(
            '/accounts/linked-emails/',
            {'email': 'DUP@example.com'},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['error'],
            'This email is already linked.',
        )

    def test_duplicate_email_for_different_user_rejected_due_to_global_uniqueness(self):
        AdditionalEmail.objects.create(user=self.other_user, email='shared@example.com')

        response = self.client.post(
            '/accounts/linked-emails/',
            {'email': 'SHARED@example.com'},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'This email is already linked.')

    def test_remove_linked_email_success(self):
        linked_email = AdditionalEmail.objects.create(user=self.user, email='rm@example.com')

        with patch('accounts.views.refresh_contracting_opportunities_for_user') as mock_refresh:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(
                    f'/accounts/linked-emails/{linked_email.id}/',
                    **self.auth_headers,
                )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Email removed successfully.')
        self.assertEqual(response.data['removed_id'], linked_email.id)
        self.assertTrue(response.data['opportunities_refreshed'])
        self.assertFalse(AdditionalEmail.objects.filter(id=linked_email.id).exists())
        mock_refresh.assert_called_once()
        self.assertEqual(mock_refresh.call_args[0][0].id, self.user.id)

    def test_unauthorized_request_rejected(self):
        response = self.client.get('/accounts/linked-emails/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_remove_another_users_linked_email(self):
        other_email = AdditionalEmail.objects.create(user=self.other_user, email='other-linked@example.com')

        response = self.client.delete(
            f'/accounts/linked-emails/{other_email.id}/',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(AdditionalEmail.objects.filter(id=other_email.id).exists())

    def test_list_linked_emails_returns_only_current_users_emails(self):
        AdditionalEmail.objects.create(user=self.user, email='mine@example.com')
        AdditionalEmail.objects.create(user=self.other_user, email='notmine@example.com')

        response = self.client.get('/accounts/linked-emails/', **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['emails']), 1)
        self.assertEqual(response.data['emails'][0]['email'], 'mine@example.com')


class AuthApiTests(APITestCase):
    def test_signup_creates_user_and_session(self):
        response = self.client.post(
            '/accounts/signup/',
            {'email': 'newuser@example.com', 'password': 'StrongPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_authenticates_user_and_creates_session(self):
        user = User.objects.create_user(
            email='loginuser@example.com',
            password='StrongPass123!',
        )

        response = self.client.post(
            '/accounts/login/',
            {'email': 'loginuser@example.com', 'password': 'StrongPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)
