import base64
import html
import re
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.mailbox_provider import get_mailbox_provider_client, stable_external_message_id
from accounts.models import AdditionalEmail, ConnectedAccount, MailboxConnection, MailboxContract
from contracts.management.services.email_filters import classify_contract_email
from contracts.management.services.email_parser import parse_contract_from_email
from contracts.models import Contract, EmailIngestionMessage


CONTRACT_KEYWORDS = [
    "contract",
    "solicitation",
    "rfp",
    "rfq",
    "rfi",
    "proposal",
    "bid",
    "procurement",
    "opportunity",
    "award",
    "quote",
    "subcontract",
    "sam.gov",
]

GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
OUTLOOK_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
OUTLOOK_MESSAGES_URL = "https://graph.microsoft.com/v1.0/me/messages"


class MailboxSyncError(Exception):
    pass


def serialize_mailbox_connection(connection):
    return {
        "id": connection.id,
        "additional_email_id": connection.additional_email_id,
        "provider": connection.provider,
        "mailbox_email": connection.mailbox_email,
        "expires_at": connection.expires_at,
        "scope": connection.scope,
        "status": connection.status,
        "last_synced_at": connection.last_synced_at,
        "sync_cursor": connection.sync_cursor,
        "created_at": connection.created_at,
        "updated_at": connection.updated_at,
    }


def create_or_update_mailbox_connection(user, payload):
    provider = (payload.get("provider") or MailboxConnection.Provider.GMAIL).strip().lower()
    mailbox_email = (payload.get("mailbox_email") or payload.get("email") or "").strip().lower()
    additional_email_id = payload.get("additional_email_id")

    if provider not in MailboxConnection.Provider.values:
        raise ValidationError("Unsupported mailbox provider.")

    if not mailbox_email:
        raise ValidationError("mailbox_email is required.")

    additional_email = None
    if additional_email_id:
        additional_email = AdditionalEmail.objects.filter(
            id=additional_email_id,
            user=user,
        ).first()
        if not additional_email:
            raise PermissionDenied("Linked email not found for this user.")

        if additional_email.email.lower() != mailbox_email:
            raise ValidationError("mailbox_email must match the linked email.")
    else:
        additional_email = AdditionalEmail.objects.filter(
            user=user,
            email__iexact=mailbox_email,
        ).first()

    expires_at = payload.get("expires_at")
    if isinstance(expires_at, str) and expires_at:
        expires_at = parse_datetime(expires_at)
        if expires_at and timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())

    defaults = {
        "additional_email": additional_email,
        "expires_at": expires_at,
        "scope": (payload.get("scope") or "").strip(),
        "status": MailboxConnection.Status.CONNECTED,
    }

    connection, _created = MailboxConnection.objects.get_or_create(
        user=user,
        provider=provider,
        mailbox_email=mailbox_email,
        defaults=defaults,
    )

    for key, value in defaults.items():
        setattr(connection, key, value)

    connection.set_tokens(
        access_token=payload.get("access_token") or "",
        refresh_token=payload.get("refresh_token") or "",
    )
    connection.save()
    return connection


def get_user_mailbox_connection(user, connection_id):
    connection = MailboxConnection.objects.filter(id=connection_id, user=user).first()
    if not connection:
        raise PermissionDenied("Mailbox connection not found for this user.")
    return connection


def _message_received_at(message):
    received_at = message.get("received_at")
    if received_at:
        return received_at
    return None


def _source_email_for_message(message, connection):
    return (message.get("to_email") or connection.mailbox_email or "").strip()


def sync_mailbox_connection(connection):
    provider_client = get_mailbox_provider_client(connection.provider)
    messages = provider_client.fetch_messages(connection)

    summary = {
        "mailbox_connection_id": connection.id,
        "messages_seen": 0,
        "candidates": 0,
        "created": 0,
        "updated": 0,
        "skipped_existing": 0,
        "ignored": 0,
        "contracts": [],
    }

    for message in messages:
        summary["messages_seen"] += 1
        external_message_id = stable_external_message_id(message)
        existing = EmailIngestionMessage.objects.filter(
            mailbox_connection=connection,
            external_message_id=external_message_id,
        ).select_related("contract").first()

        if existing and existing.contract_id:
            summary["skipped_existing"] += 1
            continue

        classification = classify_contract_email(message)
        filter_reason = ", ".join(classification["reasons"])

        ingestion_message, _created = EmailIngestionMessage.objects.get_or_create(
            mailbox_connection=connection,
            external_message_id=external_message_id,
            defaults={
                "source_email": _source_email_for_message(message, connection),
                "sender": message.get("sender") or message.get("from_email") or "",
                "subject": message.get("subject") or "",
                "received_at": _message_received_at(message),
                "was_candidate": classification["is_candidate"],
                "filter_reason": filter_reason,
            },
        )

        ingestion_message.source_email = _source_email_for_message(message, connection)
        ingestion_message.sender = message.get("sender") or message.get("from_email") or ""
        ingestion_message.subject = message.get("subject") or ""
        ingestion_message.received_at = _message_received_at(message)
        ingestion_message.was_candidate = classification["is_candidate"]
        ingestion_message.filter_reason = filter_reason

        if not classification["is_candidate"]:
            ingestion_message.save()
            summary["ignored"] += 1
            continue

        summary["candidates"] += 1
        contract_data = parse_contract_from_email(message, mailbox_connection=connection)

        with transaction.atomic():
            if ingestion_message.contract_id:
                contract = ingestion_message.contract
                for field, value in contract_data.items():
                    setattr(contract, field, value)
                contract.save()
                created_contract = False
            else:
                contract = Contract.objects.create(**contract_data)
                ingestion_message.contract = contract
                created_contract = True

            ingestion_message.save()

        if created_contract:
            summary["created"] += 1
        else:
            summary["updated"] += 1

        summary["contracts"].append(
            {
                "id": contract.id,
                "title": contract.title,
                "external_message_id": external_message_id,
                "created": created_contract,
            }
        )

    connection.last_synced_at = timezone.now()
    latest_cursor = getattr(provider_client, "next_sync_cursor", "") or connection.sync_cursor
    if latest_cursor:
        connection.sync_cursor = latest_cursor
    connection.save(update_fields=["last_synced_at", "sync_cursor", "updated_at"])

    return summary


def _clean_text(value):
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _header_value(headers, name):
    expected_name = name.lower()
    for header in headers or []:
        if header.get("name", "").lower() == expected_name:
            return header.get("value", "")
    return ""


def _decode_gmail_body(payload):
    if not payload:
        return ""

    body_data = payload.get("body", {}).get("data")
    if body_data:
        padded_data = body_data + "=" * (-len(body_data) % 4)
        return base64.urlsafe_b64decode(padded_data.encode()).decode("utf-8", errors="ignore")

    parts = payload.get("parts") or []
    decoded_parts = [_decode_gmail_body(part) for part in parts]
    return " ".join(part for part in decoded_parts if part)


def _matched_contract_terms(*values):
    haystack = " ".join(_clean_text(value).lower() for value in values)
    return [keyword for keyword in CONTRACT_KEYWORDS if keyword in haystack]


def _parse_message_datetime(value):
    parsed = parse_datetime(value or "")
    if not parsed:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _request_json(method, url, *, headers=None, params=None, data=None, timeout=30):
    response = requests.request(
        method,
        url,
        headers=headers,
        params=params,
        data=data,
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise MailboxSyncError(f"Mailbox provider request failed with status {response.status_code}.")
    return response.json()


def _refresh_gmail_access_token(account):
    if not account.refresh_token:
        raise MailboxSyncError("Connected Gmail mailbox does not have a refresh token.")

    config = settings.GMAIL_OAUTH_CONFIG
    payload = _request_json(
        "POST",
        GMAIL_TOKEN_URL,
        data={
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": account.refresh_token,
            "grant_type": "refresh_token",
        },
    )
    account.access_token = payload["access_token"]
    account.token_expiry = timezone.now() + timezone.timedelta(seconds=payload.get("expires_in", 3600))
    account.save(update_fields=["access_token", "token_expiry", "updated_at"])


def _refresh_outlook_access_token(account):
    if not account.refresh_token:
        raise MailboxSyncError("Connected Outlook mailbox does not have a refresh token.")

    config = settings.MSAL_CONFIG
    payload = _request_json(
        "POST",
        OUTLOOK_TOKEN_URL,
        data={
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": account.refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(config["scope"]),
        },
    )
    account.access_token = payload["access_token"]
    account.refresh_token = payload.get("refresh_token") or account.refresh_token
    account.token_expiry = timezone.now() + timezone.timedelta(seconds=payload.get("expires_in", 3600))
    account.save(update_fields=["access_token", "refresh_token", "token_expiry", "updated_at"])


def _ensure_fresh_access_token(account):
    if account.token_expiry and account.token_expiry > timezone.now() + timezone.timedelta(minutes=2):
        return

    provider = account.provider.lower()
    if provider == "gmail":
        _refresh_gmail_access_token(account)
    elif provider == "outlook":
        _refresh_outlook_access_token(account)
    else:
        raise MailboxSyncError(f"Unsupported mailbox provider: {account.provider}")


def _iter_gmail_messages(account, limit):
    headers = {"Authorization": f"Bearer {account.access_token}"}
    listing = _request_json(
        "GET",
        GMAIL_MESSAGES_URL,
        headers=headers,
        params={
            "maxResults": limit,
            "q": " OR ".join(CONTRACT_KEYWORDS),
        },
    )

    for item in listing.get("messages", []):
        message = _request_json(
            "GET",
            f"{GMAIL_MESSAGES_URL}/{item['id']}",
            headers=headers,
            params={"format": "full"},
        )
        payload = message.get("payload", {})
        headers_list = payload.get("headers", [])
        subject = _header_value(headers_list, "Subject") or "(No subject)"
        sender = parseaddr(_header_value(headers_list, "From"))[1] or _header_value(headers_list, "From")
        body = _clean_text(message.get("snippet") or _decode_gmail_body(payload))

        yield {
            "id": message["id"],
            "subject": subject,
            "body": body,
            "sender": sender,
            "received_at": _parse_message_datetime(_header_value(headers_list, "Date")),
            "web_link": f"https://mail.google.com/mail/u/{account.email}/#inbox/{message['id']}",
        }


def _iter_outlook_messages(account, limit):
    headers = {
        "Authorization": f"Bearer {account.access_token}",
        "Prefer": 'outlook.body-content-type="text"',
    }
    payload = _request_json(
        "GET",
        OUTLOOK_MESSAGES_URL,
        headers=headers,
        params={
            "$top": limit,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,bodyPreview,receivedDateTime,from,webLink",
        },
    )

    for message in payload.get("value", []):
        email_address = (
            message.get("from", {})
            .get("emailAddress", {})
            .get("address", "")
        )
        yield {
            "id": message["id"],
            "subject": message.get("subject") or "(No subject)",
            "body": _clean_text(message.get("bodyPreview") or ""),
            "sender": email_address,
            "received_at": _parse_message_datetime(message.get("receivedDateTime")),
            "web_link": message.get("webLink") or "",
        }


def _message_to_contract(account, message, matched_terms):
    deadline = message.get("received_at")
    title = message["subject"][:255]
    summary = message.get("body") or title
    hyperlink = message.get("web_link") or f"{account.provider}:{account.email}:{message['id']}"

    contract, created = Contract.objects.update_or_create(
        hyperlink=hyperlink,
        defaults={
            "source": account.provider.lower(),
            "procurement_portal": account.provider.title(),
            "title": title,
            "summary": summary,
            "deadline": deadline,
            "agency": message.get("sender") or account.email,
            "sub_agency": "",
            "naics_code": "",
            "partner_name": message.get("sender") or "",
            "status": "Email Lead",
            "category": "",
        },
    )

    MailboxContract.objects.update_or_create(
        connected_account=account,
        provider_message_id=message["id"],
        defaults={
            "user": account.user,
            "contract": contract,
            "matched_terms": ", ".join(matched_terms)[:255],
        },
    )
    return contract, created


def sync_connected_account(account, limit=25):
    _ensure_fresh_access_token(account)

    provider = account.provider.lower()
    if provider == "gmail":
        messages = _iter_gmail_messages(account, limit)
    elif provider == "outlook":
        messages = _iter_outlook_messages(account, limit)
    else:
        raise MailboxSyncError(f"Unsupported mailbox provider: {account.provider}")

    created_count = 0
    updated_count = 0
    matched_contracts = []

    for message in messages:
        matched_terms = _matched_contract_terms(message["subject"], message["body"])
        if not matched_terms:
            continue

        contract, created = _message_to_contract(account, message, matched_terms)
        created_count += int(created)
        updated_count += int(not created)
        matched_contracts.append({
            "id": contract.id,
            "title": contract.title,
            "matched_terms": matched_terms,
        })

    account.last_synced_at = timezone.now()
    account.save(update_fields=["last_synced_at", "updated_at"])
    return {
        "id": account.id,
        "provider": account.provider,
        "email": account.email,
        "last_synced_at": account.last_synced_at.isoformat(),
        "created_count": created_count,
        "updated_count": updated_count,
        "matched_count": len(matched_contracts),
        "contracts": matched_contracts,
    }


def sync_all_connected_accounts(user, limit=25):
    synced = []
    for account in ConnectedAccount.objects.filter(user=user, is_active=True).order_by("id"):
        synced.append(sync_connected_account(account, limit=limit))
    return synced


def refresh_contracting_opportunities_for_user(user):
    connections = MailboxConnection.objects.filter(
        user=user,
        status=MailboxConnection.Status.CONNECTED,
    ).order_by("id")

    result = {
        "mailboxes_seen": connections.count(),
        "messages_seen": 0,
        "candidates": 0,
        "created": 0,
        "updated": 0,
        "skipped_existing": 0,
        "ignored": 0,
        "mailboxes": [],
        "connected_accounts_seen": 0,
        "connected_accounts": [],
    }

    for connection in connections:
        mailbox_result = sync_mailbox_connection(connection)
        result["mailboxes"].append(mailbox_result)
        for key in ("messages_seen", "candidates", "created", "updated", "skipped_existing", "ignored"):
            result[key] += mailbox_result[key]

    connected_accounts = ConnectedAccount.objects.filter(user=user, is_active=True).order_by("id")
    result["connected_accounts_seen"] = connected_accounts.count()
    for account in connected_accounts:
        result["connected_accounts"].append(sync_connected_account(account))

    return result


def refresh_user_opportunities(user):
    return refresh_contracting_opportunities_for_user(user)
