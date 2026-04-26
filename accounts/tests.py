from rest_framework import status
from rest_framework.authtoken.models import Token
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from unittest.mock import patch

from accounts.models import AdditionalEmail, MailboxConnection, User
from accounts.services import refresh_contracting_opportunities_for_user
from contracts.management.services.email_filters import classify_contract_email
from contracts.management.services.email_parser import parse_contract_from_email
from contracts.models import Contract, EmailIngestionMessage


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
        MailboxConnection.objects.create(
            user=self.user,
            additional_email=linked_email,
            provider=MailboxConnection.Provider.GMAIL,
            mailbox_email='rm@example.com',
        )

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
        self.assertFalse(MailboxConnection.objects.filter(mailbox_email='rm@example.com').exists())
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


class MailboxConnectionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='mailbox-owner@example.com',
            password='StrongPass123!',
        )
        self.other_user = User.objects.create_user(
            email='mailbox-other@example.com',
            password='StrongPass123!',
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}
        self.linked_email = AdditionalEmail.objects.create(
            user=self.user,
            email='contracts@example.com',
        )

    def test_save_mailbox_connection_stores_signed_tokens(self):
        response = self.client.post(
            '/accounts/mailbox-connections/',
            {
                'additional_email_id': self.linked_email.id,
                'provider': 'gmail',
                'mailbox_email': 'contracts@example.com',
                'access_token': 'access-token-value',
                'refresh_token': 'refresh-token-value',
                'scope': 'gmail.readonly',
            },
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        connection = MailboxConnection.objects.get(user=self.user)
        self.assertEqual(connection.provider, MailboxConnection.Provider.GMAIL)
        self.assertNotEqual(connection.access_token, 'access-token-value')
        self.assertNotEqual(connection.refresh_token, 'refresh-token-value')
        self.assertEqual(connection.get_access_token(), 'access-token-value')
        self.assertEqual(connection.get_refresh_token(), 'refresh-token-value')

    def test_save_mailbox_connection_rejects_other_users_linked_email(self):
        other_linked_email = AdditionalEmail.objects.create(
            user=self.other_user,
            email='other-contracts@example.com',
        )

        response = self.client.post(
            '/accounts/mailbox-connections/',
            {
                'additional_email_id': other_linked_email.id,
                'provider': 'gmail',
                'mailbox_email': 'other-contracts@example.com',
                'access_token': 'token',
            },
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(MailboxConnection.objects.filter(user=self.user).exists())

    def test_sync_rejects_other_users_connection(self):
        other_connection = MailboxConnection.objects.create(
            user=self.other_user,
            provider=MailboxConnection.Provider.GMAIL,
            mailbox_email='other-contracts@example.com',
        )

        response = self.client.post(
            f'/accounts/mailbox-connections/{other_connection.id}/sync/',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_mailbox_connection_success(self):
        connection = MailboxConnection.objects.create(
            user=self.user,
            provider=MailboxConnection.Provider.GMAIL,
            mailbox_email='contracts@example.com',
        )

        response = self.client.delete(
            f'/accounts/mailbox-connections/{connection.id}/',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['removed_id'], connection.id)
        self.assertFalse(MailboxConnection.objects.filter(id=connection.id).exists())

    def test_delete_mailbox_connection_rejects_other_users_connection(self):
        other_connection = MailboxConnection.objects.create(
            user=self.other_user,
            provider=MailboxConnection.Provider.GMAIL,
            mailbox_email='other-contracts@example.com',
        )

        response = self.client.delete(
            f'/accounts/mailbox-connections/{other_connection.id}/',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(MailboxConnection.objects.filter(id=other_connection.id).exists())


class EmailFilterParserTests(TestCase):
    def test_filter_accepts_contract_opportunity_email(self):
        result = classify_contract_email(
            {
                'sender': 'contracting.officer@gsa.gov',
                'subject': 'RFQ: Cloud Support Services',
                'body_text': 'Proposal due: May 15, 2026. NAICS 541512.',
                'attachment_names': ['rfq-package.pdf'],
            }
        )

        self.assertTrue(result['is_candidate'])
        self.assertIn('contract keyword', result['reasons'])

    def test_filter_rejects_non_contract_email(self):
        result = classify_contract_email(
            {
                'sender': 'newsletter@example.com',
                'subject': 'Weekly team update',
                'body_text': 'Lunch is moved to Friday.',
                'attachment_names': [],
            }
        )

        self.assertFalse(result['is_candidate'])

    def test_parser_extracts_structured_contract_fields(self):
        message = {
            'sender': 'Jane Buyer <jane@gsa.gov>',
            'subject': 'RFP: Cloud Migration Support',
            'body_text': (
                'Agency: General Services Administration\n'
                'Sub-agency: Technology Transformation Services\n'
                'NAICS: 541512\n'
                'Proposal due: May 15, 2026\n'
                'Review details at https://example.gov/rfp/123\n'
                'The government seeks secure cloud migration support.'
            ),
        }

        parsed = parse_contract_from_email(message)

        self.assertEqual(parsed['title'], 'Cloud Migration Support')
        self.assertIn('secure cloud migration support', parsed['summary'])
        self.assertEqual(parsed['agency'], 'General Services Administration')
        self.assertEqual(parsed['sub_agency'], 'Technology Transformation Services')
        self.assertEqual(parsed['naics_code'], '541512')
        self.assertEqual(parsed['hyperlink'], 'https://example.gov/rfp/123')
        self.assertIsNotNone(parsed['deadline'])


class FakeMailboxProvider:
    next_sync_cursor = 'cursor-2'

    def __init__(self, messages):
        self.messages = messages

    def fetch_messages(self, mailbox_connection):
        return self.messages


class MailboxSyncServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='sync-owner@example.com',
            password='StrongPass123!',
        )
        self.connection = MailboxConnection.objects.create(
            user=self.user,
            provider=MailboxConnection.Provider.GMAIL,
            mailbox_email='contracts@example.com',
        )
        self.message = {
            'external_message_id': 'gmail-msg-1',
            'sender': 'contracting@gsa.gov',
            'from_email': 'contracting@gsa.gov',
            'to_email': 'contracts@example.com',
            'subject': 'RFQ: Data Platform Support',
            'body_text': (
                'Agency: GSA\n'
                'NAICS Code: 541512\n'
                'Quotes due: 05/15/2026\n'
                'Solicitation details: https://example.gov/solicitation\n'
                'This is a contract opportunity for data platform support.'
            ),
            'attachment_names': ['solicitation.pdf'],
            'received_at': timezone.now(),
        }

    def test_refresh_service_creates_contract_from_candidate_message(self):
        with patch(
            'accounts.services.get_mailbox_provider_client',
            return_value=FakeMailboxProvider([self.message]),
        ):
            result = refresh_contracting_opportunities_for_user(self.user)

        self.assertEqual(result['mailboxes_seen'], 1)
        self.assertEqual(result['messages_seen'], 1)
        self.assertEqual(result['candidates'], 1)
        self.assertEqual(result['created'], 1)
        self.assertEqual(Contract.objects.count(), 1)

        contract = Contract.objects.first()
        self.assertEqual(contract.source, Contract.SourceType.GMAIL)
        self.assertEqual(contract.title, 'Data Platform Support')
        self.assertEqual(contract.agency, 'GSA')
        self.assertEqual(contract.naics_code, '541512')

        ingestion = EmailIngestionMessage.objects.get()
        self.assertEqual(ingestion.contract, contract)
        self.assertEqual(ingestion.external_message_id, 'gmail-msg-1')
        self.assertTrue(ingestion.was_candidate)

        self.connection.refresh_from_db()
        self.assertIsNotNone(self.connection.last_synced_at)
        self.assertEqual(self.connection.sync_cursor, 'cursor-2')

    def test_refresh_service_dedupes_same_external_message_id(self):
        with patch(
            'accounts.services.get_mailbox_provider_client',
            return_value=FakeMailboxProvider([self.message]),
        ):
            first = refresh_contracting_opportunities_for_user(self.user)
            second = refresh_contracting_opportunities_for_user(self.user)

        self.assertEqual(first['created'], 1)
        self.assertEqual(second['created'], 0)
        self.assertEqual(second['skipped_existing'], 1)
        self.assertEqual(Contract.objects.count(), 1)
        self.assertEqual(EmailIngestionMessage.objects.count(), 1)
