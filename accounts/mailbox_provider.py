import hashlib


class MailboxProviderClient:
    def fetch_messages(self, mailbox_connection):
        return []


class NoopMailboxProviderClient(MailboxProviderClient):
    pass


def stable_external_message_id(message):
    external_id = message.get("external_message_id") or message.get("id")
    if external_id:
        return str(external_id)

    fingerprint = "|".join(
        str(message.get(key) or "")
        for key in ("sender", "from_email", "subject", "received_at", "body_text")
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def get_mailbox_provider_client(provider):
    # Real Gmail/Outlook API clients should be selected here when OAuth
    # credentials and provider SDK/API code are available. The default keeps
    # local tests deterministic and avoids network access.
    return NoopMailboxProviderClient()
