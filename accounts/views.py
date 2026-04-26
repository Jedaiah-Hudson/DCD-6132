from django.shortcuts import redirect, render
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate, login as django_login
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView
from accounts.models import User
from accounts.models import AdditionalEmail
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .serializers import PasswordResetConfirmSerializer
from .serializers import PasswordResetRequestSerializer
from .utils import generate_reset_token, get_reset_token_expiration, send_password_reset_email
from .services import (
    MailboxSyncError,
    create_or_update_mailbox_connection,
    get_user_mailbox_connection,
    refresh_contracting_opportunities_for_user,
    serialize_mailbox_connection,
    sync_all_connected_accounts,
    sync_connected_account,
    sync_mailbox_connection,
)
from django.conf import settings
import msal
import requests
from urllib.parse import urlencode
from .models import ConnectedAccount
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core import signing

# Create your views here.

GMAIL_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GMAIL_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GMAIL_PROFILE_URL = 'https://gmail.googleapis.com/gmail/v1/users/me/profile'
GMAIL_STATE_SALT = 'gmail-oauth-state'


def _get_gmail_oauth_config():
    config = settings.GMAIL_OAUTH_CONFIG
    missing_fields = [
        field for field in ('client_id', 'client_secret', 'redirect_uri')
        if not config.get(field)
    ]
    if missing_fields:
        raise ValueError(f"Missing Gmail OAuth setting(s): {', '.join(missing_fields)}")
    return config


def _make_gmail_oauth_state(user):
    signer = signing.TimestampSigner(salt=GMAIL_STATE_SALT)
    return signer.sign(str(user.id))


def _get_user_from_gmail_oauth_state(state):
    signer = signing.TimestampSigner(salt=GMAIL_STATE_SALT)
    user_id = signer.unsign(state, max_age=600)
    return User.objects.get(id=user_id)


# view to login api endpoints
@api_view(['POST'])
def login_api(request):
    email = (request.data.get('email') or '').strip().lower()
    password = request.data.get('password') or ''

    if not email or not password:
        return Response(
            {
                "success": False,
                "message": "Email and password are required."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Authenticate against the configured custom user model backend.
    user = authenticate(request, username=email, password=password)
    if not user:
        return Response(
            {
                "success": False,
                "message": "Invalid email or password."
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    #create/get token for user
    token, created = Token.objects.get_or_create(user=user)
    django_login(request, user)
    return Response({
        "success": True,
        "message": "Login Successful!",
        "token": token.key,
        "user": {
            "id": user.id,
            "email": user.email
        }
    }, status=status.HTTP_200_OK)

def login_view(request):
    return render(request, 'accounts/login.html')

@api_view(['POST'])
def signup_api(request):
    email = (request.data.get('email') or '').strip().lower()
    password = request.data.get('password') or ''

    if not email or not password:
        return Response(
            {
                "success": False,
                "message": "Email and password are required."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(email=email).exists():
        return Response({
            "success": False,
            "message": "Email already registered."
        }, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(email=email, password=password)

    token = Token.objects.create(user=user)
    django_login(request, user)

    return Response({
        "success": True,
        "message": "Account created successfully!",
        "token": token.key,
        "user": {
            "id": user.id,
            "email": user.email
        }
    }, status=status.HTTP_201_CREATED)

def signup_view(request):
    return render(request, 'accounts/signUp.html')


User = get_user_model()

class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # safer to avoid revealing whether email exists
            return Response(
                {"message": "If an account with that email exists, a reset link has been sent."},
                status=status.HTTP_200_OK
            )

        token = generate_reset_token()
        expiration = get_reset_token_expiration()

        user.reset_token = token
        user.reset_token_expiration = expiration
        user.save(update_fields=["reset_token", "reset_token_expiration"])

        reset_link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={token}"
        # replace localhost:3000 with your frontend URL later

        
        send_password_reset_email(user, reset_link)

        return Response(
            {
                "message": "If an account with that email exists, a reset link has been sent.",
                "reset_link_placeholder": reset_link  # remove later in production
            },
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(reset_token=token)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid reset token."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.reset_token_expiration:
            return Response(
                {"error": "Reset token is invalid."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.reset_token_expiration < timezone.now():
            return Response(
                {"error": "Reset token has expired."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as e:
            return Response(
                {"error": e.messages},
                status=status.HTTP_400_BAD_REQUEST
            )

## user password is update an dtokeninfo is cleared
        user.set_password(new_password)  # hashes password properly
        user.reset_token = None
        user.reset_token_expiration = None
        user.save(update_fields=["password", "reset_token", "reset_token_expiration"])

        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK
        )


@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def linked_emails_api(request):
    if request.method == 'GET':
        emails = AdditionalEmail.objects.filter(user=request.user).order_by('id')
        serialized = [
            {
                'id': email.id,
                'email': email.email,
                'label': email.label,
            }
            for email in emails
        ]
        return Response({'emails': serialized}, status=status.HTTP_200_OK)

    raw_email = (request.data.get('email') or '').strip()
    normalized_email = raw_email.lower()
    label = (request.data.get('label') or '').strip()

    try:
        validate_email(normalized_email)
    except ValidationError:
        return Response(
            {'error': 'Invalid email format.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if AdditionalEmail.objects.filter(email__iexact=normalized_email).exists():
        return Response(
            {'error': 'This email is already linked.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    linked_email = AdditionalEmail.objects.create(
        user=request.user,
        email=normalized_email,
        label=label,
    )
    user = request.user
    transaction.on_commit(lambda: refresh_contracting_opportunities_for_user(user))

    return Response(
        {
            'message': 'Email added successfully.',
            'email': {
                'id': linked_email.id,
                'email': linked_email.email,
                'label': linked_email.label,
            },
            'opportunities_refreshed': True,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def linked_email_detail_api(request, email_id):
    linked_email = AdditionalEmail.objects.filter(
        id=email_id,
        user=request.user,
    ).first()
    if not linked_email:
        return Response({'error': 'Linked email not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    linked_email.delete()
    transaction.on_commit(lambda: refresh_contracting_opportunities_for_user(user))
    return Response(
        {
            'message': 'Email removed successfully.',
            'removed_id': email_id,
            'opportunities_refreshed': True,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def mailbox_connections_api(request):
    if request.method == 'GET':
        connections = request.user.mailbox_connections.order_by('id')
        return Response(
            {'mailbox_connections': [serialize_mailbox_connection(connection) for connection in connections]},
            status=status.HTTP_200_OK,
        )

    try:
        connection = create_or_update_mailbox_connection(request.user, request.data)
    except PermissionDenied as exc:
        return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as exc:
        message = exc.messages[0] if hasattr(exc, 'messages') else str(exc)
        return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            'message': 'Mailbox connected successfully.',
            'mailbox_connection': serialize_mailbox_connection(connection),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def mailbox_connection_sync_api(request, connection_id):
    try:
        connection = get_user_mailbox_connection(request.user, connection_id)
    except PermissionDenied as exc:
        return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)

    result = sync_mailbox_connection(connection)
    return Response({'message': 'Mailbox sync completed.', 'result': result}, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def mailbox_connections_sync_api(request):
    result = refresh_contracting_opportunities_for_user(request.user)
    return Response({'message': 'Mailbox sync completed.', 'result': result}, status=status.HTTP_200_OK)
# views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import NAICSCode
from .serializers import NAICSCodeSerializer

@api_view(['GET'])
def naics_list(request):
    naics = NAICSCode.objects.all()
    serializer = NAICSCodeSerializer(naics, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def gmail_auth(request):
    """Start Gmail OAuth authorization and return Google's consent URL."""
    try:
        config = _get_gmail_oauth_config()
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    params = {
        'client_id': config['client_id'],
        'redirect_uri': config['redirect_uri'],
        'response_type': 'code',
        'scope': ' '.join(config['scope']),
        'access_type': 'offline',
        'include_granted_scopes': 'true',
        'prompt': 'consent',
        'state': _make_gmail_oauth_state(request.user),
    }

    return Response({'auth_url': f"{GMAIL_AUTH_URL}?{urlencode(params)}"}, status=status.HTTP_200_OK)


def gmail_callback(request):
    """Exchange Google's authorization code for tokens and store the Gmail mailbox."""
    code = request.GET.get('code')
    state = request.GET.get('state')
    oauth_error = request.GET.get('error')

    if oauth_error:
        return JsonResponse({'error': oauth_error}, status=400)

    if not code or not state:
        return JsonResponse({'error': 'Missing authorization code or state.'}, status=400)

    try:
        user = _get_user_from_gmail_oauth_state(state)
        config = _get_gmail_oauth_config()
    except (signing.BadSignature, signing.SignatureExpired, User.DoesNotExist):
        return JsonResponse({'error': 'Invalid or expired OAuth state.'}, status=400)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=500)

    token_response = requests.post(
        GMAIL_TOKEN_URL,
        data={
            'code': code,
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'redirect_uri': config['redirect_uri'],
            'grant_type': 'authorization_code',
        },
        timeout=30,
    )

    if token_response.status_code != 200:
        return JsonResponse({'error': 'Failed to exchange Gmail authorization code.'}, status=400)

    token_data = token_response.json()
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')

    if not access_token:
        return JsonResponse({'error': 'Google did not return an access token.'}, status=400)

    profile_response = requests.get(
        GMAIL_PROFILE_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=30,
    )

    if profile_response.status_code != 200:
        return JsonResponse({'error': 'Failed to fetch Gmail mailbox profile.'}, status=400)

    gmail_address = (profile_response.json().get('emailAddress') or '').strip().lower()
    if not gmail_address:
        return JsonResponse({'error': 'Google did not return a Gmail address.'}, status=400)

    existing_account = ConnectedAccount.objects.filter(
        user=user,
        email__iexact=gmail_address,
    ).first()
    saved_refresh_token = refresh_token or (existing_account.refresh_token if existing_account else None)

    if not saved_refresh_token:
        return JsonResponse(
            {'error': 'Google did not return a refresh token. Reconnect Gmail and approve offline access.'},
            status=400,
        )

    account, _created = ConnectedAccount.objects.update_or_create(
        user=user,
        email=gmail_address,
        defaults={
            'provider': 'gmail',
            'access_token': access_token,
            'refresh_token': saved_refresh_token,
            'token_expiry': timezone.now() + timezone.timedelta(seconds=token_data.get('expires_in', 3600)),
            'is_active': True,
        },
    )

    return redirect(f"{settings.FRONTEND_BASE_URL}/profile?gmail=connected&account={account.id}")


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def connected_accounts_api(request):
    accounts = ConnectedAccount.objects.filter(user=request.user).order_by('provider', 'email')
    return Response(
        {
            'mailboxes': [
                {
                    'id': account.id,
                    'provider': account.provider,
                    'email': account.email,
                    'is_active': account.is_active,
                    'last_synced_at': account.last_synced_at.isoformat() if account.last_synced_at else None,
                    'status': 'Connected' if account.is_active else 'Needs attention',
                }
                for account in accounts
            ],
        },
        status=status.HTTP_200_OK,
    )


@login_required
def outlook_auth(request):
    """Start the Outlook OAuth authorization flow."""
    client = msal.ConfidentialClientApplication(
        settings.MSAL_CONFIG['client_id'],
        authority=settings.MSAL_CONFIG['authority'],
        client_credential=settings.MSAL_CONFIG['client_secret']
    )
    auth_url = client.get_authorization_request_url(
        settings.MSAL_CONFIG['scope'],
        redirect_uri=settings.MSAL_CONFIG['redirect_uri']
    )
    return JsonResponse({'auth_url': auth_url})  # Frontend can redirect to this URL

@login_required
def outlook_callback(request):
    """Handle the OAuth callback, exchange code for tokens, and store in ConnectedAccount."""
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'error': 'No authorization code provided'}, status=400)

    client = msal.ConfidentialClientApplication(
        settings.MSAL_CONFIG['client_id'],
        authority=settings.MSAL_CONFIG['authority'],
        client_credential=settings.MSAL_CONFIG['client_secret']
    )

    # Exchange code for tokens
    result = client.acquire_token_by_authorization_code(
        code,
        scopes=settings.MSAL_CONFIG['scope'],
        redirect_uri=settings.MSAL_CONFIG['redirect_uri']
    )

    if 'access_token' not in result:
        return JsonResponse({'error': 'Failed to acquire token'}, status=400)

    # Get user email from Graph (requires User.Read scope)
    import requests
    headers = {'Authorization': f'Bearer {result["access_token"]}'}
    user_response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
    if user_response.status_code != 200:
        return JsonResponse({'error': 'Failed to fetch user info'}, status=400)
    user_email = user_response.json().get('mail') or user_response.json().get('userPrincipalName')

    # Store in ConnectedAccount
    account, created = ConnectedAccount.objects.update_or_create(
        user=request.user,
        email=user_email,
        defaults={
            'provider': 'outlook',
            'access_token': result['access_token'],
            'refresh_token': result.get('refresh_token'),
            'token_expiry': timezone.now() + timezone.timedelta(seconds=result.get('expires_in', 3600)),
            'is_active': True,
        }
    )

    return redirect('/dashboard/')  # Redirect to a success page, e.g., dashboard

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def sync_mailbox(request, account_id):
    try:
        account = ConnectedAccount.objects.get(pk=account_id, user=request.user)
    except ConnectedAccount.DoesNotExist:
        return Response({'success': False, 'error': 'Mailbox not found'}, status=status.HTTP_404_NOT_FOUND)

    limit = _parse_sync_limit(request.data.get('limit', 25))
    try:
        result = sync_connected_account(account, limit=limit)
    except MailboxSyncError as exc:
        return Response(
            {
                'success': False,
                'error': str(exc),
                'mailbox': {
                    'id': account.id,
                    'provider': account.provider,
                    'email': account.email,
                    'last_synced_at': account.last_synced_at.isoformat() if account.last_synced_at else None,
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({'success': True, 'mailbox': result}, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def sync_all_mailboxes(request):
    limit = _parse_sync_limit(request.data.get('limit', 25))
    synced = []
    failed = []

    for account in request.user.connected_accounts.filter(is_active=True).order_by('id'):
        try:
            synced.append(sync_connected_account(account, limit=limit))
        except MailboxSyncError as exc:
            failed.append({
                'id': account.id,
                'provider': account.provider,
                'email': account.email,
                'error': str(exc),
                'last_synced_at': account.last_synced_at.isoformat() if account.last_synced_at else None,
            })

    return Response({
        'success': len(failed) == 0,
        'synced_count': len(synced),
        'failed_count': len(failed),
        'mailboxes': synced,
        'failed_mailboxes': failed,
    }, status=status.HTTP_200_OK)


def _parse_sync_limit(value):
    try:
        return max(1, min(int(value), 100))
    except (TypeError, ValueError):
        return 25
