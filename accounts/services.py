from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.mailbox_provider import get_mailbox_provider_client, stable_external_message_id
from accounts.models import AdditionalEmail, MailboxConnection
from contracts.management.services.email_filters import classify_contract_email
from contracts.management.services.email_parser import parse_contract_from_email
from contracts.models import Contract, EmailIngestionMessage


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
    }

    for connection in connections:
        mailbox_result = sync_mailbox_connection(connection)
        result["mailboxes"].append(mailbox_result)
        for key in ("messages_seen", "candidates", "created", "updated", "skipped_existing", "ignored"):
            result[key] += mailbox_result[key]

    return result


def refresh_user_opportunities(user):
    return refresh_contracting_opportunities_for_user(user)
