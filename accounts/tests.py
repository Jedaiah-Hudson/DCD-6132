from rest_framework import status
from rest_framework.authtoken.models import Token
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.core import signing
from django.test import override_settings

from accounts.models import AdditionalEmail, ConnectedAccount, MailboxConnection, MailboxContract, User
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


@override_settings(
    GMAIL_OAUTH_CONFIG={
        'client_id': 'google-client-id',
        'client_secret': 'google-client-secret',
        'redirect_uri': 'http://127.0.0.1:8000/accounts/gmail/callback/',
        'scope': ['https://www.googleapis.com/auth/gmail.readonly'],
    },
    MSAL_CONFIG={
        'client_id': 'microsoft-client-id',
        'client_secret': 'microsoft-client-secret',
        'authority': 'https://login.microsoftonline.com/common',
        'redirect_uri': 'http://127.0.0.1:8000/accounts/outlook/callback/',
        'scope': [
            'offline_access',
            'https://graph.microsoft.com/Mail.Read',
            'https://graph.microsoft.com/User.Read',
        ],
    },
    FRONTEND_BASE_URL='http://localhost:5173',
)
class GmailOAuthApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='gmail-owner@example.com',
            password='StrongPass123!',
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

    def test_gmail_auth_starts_flow_with_offline_access(self):
        response = self.client.get('/accounts/gmail/auth/', **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auth_url = response.data['auth_url']
        parsed_url = urlparse(auth_url)
        params = parse_qs(parsed_url.query)

        self.assertEqual(parsed_url.netloc, 'accounts.google.com')
        self.assertEqual(params['client_id'], ['google-client-id'])
        self.assertEqual(params['redirect_uri'], ['http://127.0.0.1:8000/accounts/gmail/callback/'])
        self.assertEqual(params['response_type'], ['code'])
        self.assertEqual(params['access_type'], ['offline'])
        self.assertEqual(params['prompt'], ['consent'])
        self.assertEqual(params['include_granted_scopes'], ['true'])
        self.assertIn('https://www.googleapis.com/auth/gmail.readonly', params['scope'][0])
        self.assertIn('state', params)

    @patch('accounts.views.requests.get')
    @patch('accounts.views.requests.post')
    def test_gmail_callback_exchanges_code_and_saves_connected_account(self, mock_post, mock_get):
        signer = signing.TimestampSigner(salt='gmail-oauth-state')
        oauth_state = signer.sign(str(self.user.id))

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'access_token': 'access-token-value',
            'refresh_token': 'refresh-token-value',
            'expires_in': 3600,
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'emailAddress': 'ConnectedUser@Gmail.com',
        }

        response = self.client.get(
            '/accounts/gmail/callback/',
            {'code': 'auth-code', 'state': oauth_state},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('http://localhost:5173/profile?gmail=connected'))

        account = ConnectedAccount.objects.get(user=self.user, email='connecteduser@gmail.com')
        self.assertEqual(account.provider, 'gmail')
        self.assertEqual(account.access_token, 'access-token-value')
        self.assertEqual(account.refresh_token, 'refresh-token-value')
        self.assertTrue(account.is_active)

        mock_post.assert_called_once()
        token_request = mock_post.call_args.kwargs['data']
        self.assertEqual(token_request['code'], 'auth-code')
        self.assertEqual(token_request['client_id'], 'google-client-id')
        self.assertEqual(token_request['client_secret'], 'google-client-secret')
        self.assertEqual(token_request['grant_type'], 'authorization_code')

    def test_gmail_callback_rejects_invalid_state(self):
        response = self.client.get(
            '/accounts/gmail/callback/',
            {'code': 'auth-code', 'state': 'bad-state'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/profile?gmail=error', response.url)
        self.assertIn('message=Invalid+or+expired+OAuth+state.', response.url)
        self.assertFalse(ConnectedAccount.objects.exists())

    @patch('accounts.views.requests.post')
    def test_gmail_callback_redirects_token_exchange_error_detail_to_profile(self, mock_post):
        signer = signing.TimestampSigner(salt='gmail-oauth-state')
        oauth_state = signer.sign(str(self.user.id))

        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {
            'error': 'invalid_grant',
            'error_description': 'Bad Request',
        }

        response = self.client.get(
            '/accounts/gmail/callback/',
            {'code': 'auth-code', 'state': oauth_state},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/profile?gmail=error', response.url)
        self.assertIn('invalid_grant%3A+Bad+Request', response.url)
        self.assertFalse(ConnectedAccount.objects.exists())

    @patch('accounts.views.requests.get')
    @patch('accounts.views.requests.post')
    def test_gmail_callback_redirects_profile_fetch_failure_to_profile(self, mock_post, mock_get):
        signer = signing.TimestampSigner(salt='gmail-oauth-state')
        oauth_state = signer.sign(str(self.user.id))

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'access_token': 'access-token-value',
            'refresh_token': 'refresh-token-value',
            'expires_in': 3600,
        }
        mock_get.return_value.status_code = 403
        mock_get.return_value.json.return_value = {}

        response = self.client.get(
            '/accounts/gmail/callback/',
            {'code': 'auth-code', 'state': oauth_state},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('/profile?gmail=error', response.url)
        self.assertIn('message=Failed+to+fetch+Gmail+mailbox+profile.', response.url)
        self.assertFalse(ConnectedAccount.objects.exists())

    @patch('accounts.views.msal.ConfidentialClientApplication')
    def test_outlook_auth_starts_flow_with_signed_state(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client.get_authorization_request_url.return_value = 'https://login.microsoftonline.com/oauth-url'

        response = self.client.get('/accounts/outlook/auth/', **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['auth_url'], 'https://login.microsoftonline.com/oauth-url')
        mock_client_class.assert_called_once_with(
            'microsoft-client-id',
            authority='https://login.microsoftonline.com/common',
            client_credential='microsoft-client-secret',
        )
        auth_call = mock_client.get_authorization_request_url.call_args
        self.assertEqual(auth_call.args[0], [
            'offline_access',
            'https://graph.microsoft.com/Mail.Read',
            'https://graph.microsoft.com/User.Read',
        ])
        self.assertEqual(auth_call.kwargs['redirect_uri'], 'http://127.0.0.1:8000/accounts/outlook/callback/')
        self.assertIn('state', auth_call.kwargs)

    @patch('accounts.views.requests.get')
    @patch('accounts.views.msal.ConfidentialClientApplication')
    def test_outlook_callback_exchanges_code_and_saves_connected_account(self, mock_client_class, mock_get):
        signer = signing.TimestampSigner(salt='outlook-oauth-state')
        oauth_state = signer.sign(str(self.user.id))
        mock_client = mock_client_class.return_value
        mock_client.acquire_token_by_authorization_code.return_value = {
            'access_token': 'outlook-access-token',
            'refresh_token': 'outlook-refresh-token',
            'expires_in': 3600,
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'mail': 'ConnectedUser@Outlook.com',
            'userPrincipalName': 'fallback@outlook.com',
        }

        response = self.client.get(
            '/accounts/outlook/callback/',
            {'code': 'outlook-auth-code', 'state': oauth_state},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('http://localhost:5173/profile?outlook=connected'))

        account = ConnectedAccount.objects.get(user=self.user, email='connecteduser@outlook.com')
        self.assertEqual(account.provider, 'outlook')
        self.assertEqual(account.access_token, 'outlook-access-token')
        self.assertEqual(account.refresh_token, 'outlook-refresh-token')
        self.assertTrue(account.is_active)


class ConnectedAccountSyncServiceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='sync-owner@example.com',
            password='StrongPass123!',
        )
        self.other_user = User.objects.create_user(
            email='sync-other@example.com',
            password='StrongPass123!',
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

    def _connected_account(self, provider, email):
        return ConnectedAccount.objects.create(
            user=self.user,
            provider=provider,
            email=email,
            access_token=f'{provider}-access-token',
            refresh_token=f'{provider}-refresh-token',
            token_expiry=timezone.now() + timezone.timedelta(hours=1),
            is_active=True,
        )

    @patch('accounts.services.requests.request')
    def test_sync_selected_gmail_mailbox_reads_contract_messages(self, mock_request):
        account = self._connected_account('gmail', 'gmailbox@example.com')

        def response_for(method, url, **kwargs):
            response = type('Response', (), {})()
            response.status_code = 200
            if url.endswith('/messages'):
                response.json = lambda: {'messages': [{'id': 'gmail-message-1'}]}
                return response
            response.json = lambda: {
                'id': 'gmail-message-1',
                'snippet': 'Solicitation ID: RFP-2026-001. Attached is the RFP package for this contract opportunity.',
                'payload': {
                    'headers': [
                        {'name': 'Subject', 'value': 'New RFP contract opportunity'},
                        {'name': 'From', 'value': 'Buyer <buyer@example.gov>'},
                        {'name': 'Date', 'value': 'Fri, 24 Apr 2026 10:00:00 +0000'},
                    ],
                    'body': {},
                },
            }
            return response

        mock_request.side_effect = response_for

        response = self.client.post(
            f'/accounts/connected-accounts/{account.id}/sync/',
            {'limit': 1},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mailbox']['matched_count'], 1)
        contract = Contract.objects.get(title='New RFP contract opportunity')
        self.assertEqual(contract.source, Contract.SourceType.GMAIL)
        self.assertTrue(
            MailboxContract.objects.filter(
                user=self.user,
                connected_account=account,
                contract=contract,
                provider_message_id='gmail-message-1',
            ).exists()
        )
        list_request = mock_request.call_args_list[0]
        self.assertEqual(
            list_request.kwargs['params'],
            {
                'maxResults': 1,
                'q': 'category:primary',
            },
        )

    @patch('accounts.services.requests.request')
    def test_sync_selected_gmail_mailbox_skips_emoji_subjects(self, mock_request):
        account = self._connected_account('gmail', 'gmailbox@example.com')

        def response_for(method, url, **kwargs):
            response = type('Response', (), {})()
            response.status_code = 200
            if url.endswith('/messages'):
                response.json = lambda: {
                    'messages': [
                        {'id': 'emoji-message'},
                        {'id': 'plain-message'},
                    ]
                }
                return response
            if url.endswith('/emoji-message'):
                response.json = lambda: {
                    'id': 'emoji-message',
                    'snippet': 'Solicitation ID: RFP-2026-EMOJI. Attached is the RFP package for this contract opportunity.',
                    'payload': {
                        'headers': [
                            {'name': 'Subject', 'value': 'New RFP contract opportunity 🚀'},
                            {'name': 'From', 'value': 'promo@example.com'},
                        ],
                        'body': {},
                    },
                }
                return response
            response.json = lambda: {
                'id': 'plain-message',
                'snippet': 'Solicitation ID: RFP-2026-PLAIN. Attached is the RFP package for this contract opportunity.',
                'payload': {
                    'headers': [
                        {'name': 'Subject', 'value': 'Plain RFP contract opportunity'},
                        {'name': 'From', 'value': 'buyer@example.gov'},
                    ],
                    'body': {},
                },
            }
            return response

        mock_request.side_effect = response_for

        response = self.client.post(
            f'/accounts/connected-accounts/{account.id}/sync/',
            {'limit': 2},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mailbox']['matched_count'], 1)
        self.assertFalse(Contract.objects.filter(title='New RFP contract opportunity 🚀').exists())
        self.assertTrue(Contract.objects.filter(title='Plain RFP contract opportunity').exists())

    @patch('accounts.services.requests.request')
    def test_sync_selected_gmail_mailbox_skips_messages_without_solicitation_id(self, mock_request):
        account = self._connected_account('gmail', 'gmailbox@example.com')

        def response_for(method, url, **kwargs):
            response = type('Response', (), {})()
            response.status_code = 200
            if url.endswith('/messages'):
                response.json = lambda: {
                    'messages': [
                        {'id': 'missing-solicitation-id'},
                        {'id': 'has-solicitation-id'},
                    ]
                }
                return response
            if url.endswith('/missing-solicitation-id'):
                response.json = lambda: {
                    'id': 'missing-solicitation-id',
                    'snippet': 'Attached is the RFP package for this contract opportunity.',
                    'payload': {
                        'headers': [
                            {'name': 'Subject', 'value': 'RFP contract opportunity without identifier'},
                            {'name': 'From', 'value': 'buyer@example.gov'},
                        ],
                        'body': {},
                    },
                }
                return response
            response.json = lambda: {
                'id': 'has-solicitation-id',
                'snippet': 'Solicitation ID: RFP-2026-002. Attached is the RFP package for this contract opportunity.',
                'payload': {
                    'headers': [
                        {'name': 'Subject', 'value': 'RFP contract opportunity with identifier'},
                        {'name': 'From', 'value': 'buyer@example.gov'},
                    ],
                    'body': {},
                },
            }
            return response

        mock_request.side_effect = response_for

        response = self.client.post(
            f'/accounts/connected-accounts/{account.id}/sync/',
            {'limit': 2},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mailbox']['matched_count'], 1)
        self.assertFalse(Contract.objects.filter(title='RFP contract opportunity without identifier').exists())
        self.assertTrue(Contract.objects.filter(title='RFP contract opportunity with identifier').exists())

    @patch('accounts.services.requests.request')
    def test_sync_selected_outlook_mailbox_reads_contract_messages(self, mock_request):
        account = self._connected_account('outlook', 'outlookbox@example.com')
        response_payload = type('Response', (), {})()
        response_payload.status_code = 200
        response_payload.json = lambda: {
            'value': [
                {
                    'id': 'outlook-message-1',
                    'subject': 'Solicitation for proposal support',
                    'bodyPreview': 'Solicitation ID: SOL-2026-OUTLOOK. Please review this procurement bid opportunity.',
                    'receivedDateTime': '2026-04-24T10:00:00Z',
                    'from': {'emailAddress': {'address': 'buyer@example.gov'}},
                    'webLink': 'https://outlook.office.com/mail/item/outlook-message-1',
                }
            ]
        }
        mock_request.return_value = response_payload

        response = self.client.post(
            f'/accounts/connected-accounts/{account.id}/sync/',
            {'limit': 1},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mailbox']['matched_count'], 1)
        contract = Contract.objects.get(title='Solicitation for proposal support')
        self.assertEqual(contract.source, Contract.SourceType.OUTLOOK)
        self.assertTrue(
            MailboxContract.objects.filter(
                user=self.user,
                connected_account=account,
                contract=contract,
                provider_message_id='outlook-message-1',
            ).exists()
        )

    @patch('accounts.services.requests.request')
    def test_sync_all_mailboxes_runs_only_current_users_connected_accounts(self, mock_request):
        gmail_account = self._connected_account('gmail', 'gmailbox@example.com')
        outlook_account = self._connected_account('outlook', 'outlookbox@example.com')
        ConnectedAccount.objects.create(
            user=self.other_user,
            provider='gmail',
            email='other-gmailbox@example.com',
            access_token='other-token',
            refresh_token='other-refresh-token',
            token_expiry=timezone.now() + timezone.timedelta(hours=1),
            is_active=True,
        )

        def response_for(method, url, **kwargs):
            response = type('Response', (), {})()
            response.status_code = 200
            if 'gmail.googleapis.com' in url and url.endswith('/messages'):
                response.json = lambda: {'messages': [{'id': 'gmail-message-all'}]}
                return response
            if 'gmail.googleapis.com' in url:
                response.json = lambda: {
                    'id': 'gmail-message-all',
                    'snippet': 'Solicitation ID: SOL-2026-GMAIL. Contract bid details',
                    'payload': {
                        'headers': [
                            {'name': 'Subject', 'value': 'Gmail contract bid'},
                            {'name': 'From', 'value': 'buyer@example.gov'},
                        ],
                    },
                }
                return response

            response.json = lambda: {
                'value': [
                    {
                        'id': 'outlook-message-all',
                        'subject': 'Outlook RFP notice',
                        'bodyPreview': 'Solicitation ID: SOL-2026-OUTLOOK. Proposal opportunity details',
                        'from': {'emailAddress': {'address': 'buyer@example.gov'}},
                        'webLink': 'https://outlook.office.com/mail/item/outlook-message-all',
                    }
                ]
            }
            return response

        mock_request.side_effect = response_for

        response = self.client.post(
            '/accounts/connected-accounts/sync-all/',
            {'limit': 1},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['synced_count'], 2)
        self.assertEqual(
            set(MailboxContract.objects.values_list('connected_account_id', flat=True)),
            {gmail_account.id, outlook_account.id},
        )

    def test_email_contracts_are_visible_only_to_associated_user(self):
        account = self._connected_account('gmail', 'gmailbox@example.com')
        contract = Contract.objects.create(
            source=Contract.SourceType.GMAIL,
            title='Private mailbox RFP',
            summary='Contract opportunity from email.',
            agency='buyer@example.gov',
            status='Email Lead',
        )
        MailboxContract.objects.create(
            user=self.user,
            connected_account=account,
            contract=contract,
            provider_message_id='private-message',
            matched_terms='rfp, contract',
        )

        owner_response = self.client.get('/api/opportunities/', **self.auth_headers)
        other_token = Token.objects.create(user=self.other_user)
        other_response = self.client.get(
            '/api/opportunities/',
            HTTP_AUTHORIZATION=f'Token {other_token.key}',
        )
        anonymous_response = self.client.get('/api/opportunities/')

        self.assertTrue(any(item['id'] == contract.id for item in owner_response.data))
        self.assertFalse(any(item['id'] == contract.id for item in other_response.data))
        self.assertFalse(any(item['id'] == contract.id for item in anonymous_response.data))

    def test_connected_accounts_list_returns_current_users_mailboxes(self):
        account = self._connected_account('gmail', 'gmailbox@example.com')
        ConnectedAccount.objects.create(
            user=self.other_user,
            provider='outlook',
            email='other@example.com',
            access_token='other-token',
            refresh_token='other-refresh-token',
            token_expiry=timezone.now() + timezone.timedelta(hours=1),
            is_active=True,
        )

        response = self.client.get('/accounts/connected-accounts/', **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['mailboxes']), 1)
        self.assertEqual(response.data['mailboxes'][0]['id'], account.id)
        self.assertEqual(response.data['mailboxes'][0]['email'], 'gmailbox@example.com')

    @patch('accounts.services.requests.request')
    def test_sync_selected_mailbox_updates_last_sync_timestamp(self, mock_request):
        account = self._connected_account('outlook', 'outlookbox@example.com')
        response_payload = type('Response', (), {})()
        response_payload.status_code = 200
        response_payload.json = lambda: {'value': []}
        mock_request.return_value = response_payload

        response = self.client.post(
            f'/accounts/connected-accounts/{account.id}/sync/',
            {'limit': 1},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        account.refresh_from_db()
        self.assertIsNotNone(account.last_synced_at)
        self.assertEqual(response.data['mailbox']['last_synced_at'], account.last_synced_at.isoformat())

    @patch('accounts.views.sync_connected_account')
    def test_sync_selected_mailbox_returns_failure_response(self, mock_sync):
        from accounts.services import MailboxSyncError

        account = self._connected_account('gmail', 'gmailbox@example.com')
        mock_sync.side_effect = MailboxSyncError('Provider token expired.')

        response = self.client.post(
            f'/accounts/connected-accounts/{account.id}/sync/',
            {'limit': 1},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['error'], 'Provider token expired.')
        account.refresh_from_db()
        self.assertIsNone(account.last_synced_at)

    @patch('accounts.services.requests.request')
    def test_sync_selected_mailbox_returns_provider_error_detail(self, mock_request):
        account = self._connected_account('gmail', 'gmailbox@example.com')
        response_payload = type('Response', (), {})()
        response_payload.status_code = 400
        response_payload.json = lambda: {
            'error': {
                'message': 'Invalid Gmail search query.',
            }
        }
        mock_request.return_value = response_payload

        response = self.client.post(
            f'/accounts/connected-accounts/{account.id}/sync/',
            {'limit': 1},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(
            response.data['error'],
            'Mailbox provider request failed with status 400: Invalid Gmail search query.',
        )
        account.refresh_from_db()
        self.assertIsNone(account.last_synced_at)

    @patch('accounts.views.sync_connected_account')
    def test_sync_all_mailboxes_returns_partial_failure_response(self, mock_sync):
        from accounts.services import MailboxSyncError

        gmail_account = self._connected_account('gmail', 'gmailbox@example.com')
        outlook_account = self._connected_account('outlook', 'outlookbox@example.com')

        def sync_result(account, limit=25):
            if account.id == gmail_account.id:
                return {
                    'id': account.id,
                    'provider': account.provider,
                    'email': account.email,
                    'last_synced_at': timezone.now().isoformat(),
                    'created_count': 0,
                    'updated_count': 0,
                    'matched_count': 0,
                    'contracts': [],
                }
            raise MailboxSyncError('Outlook provider failed.')

        mock_sync.side_effect = sync_result

        response = self.client.post(
            '/accounts/connected-accounts/sync-all/',
            {'limit': 1},
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['synced_count'], 1)
        self.assertEqual(response.data['failed_count'], 1)
        self.assertEqual(response.data['mailboxes'][0]['id'], gmail_account.id)
        self.assertEqual(response.data['failed_mailboxes'][0]['id'], outlook_account.id)


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
