import re


CONTRACT_KEYWORDS = {
    "rfp",
    "rfq",
    "rfi",
    "solicitation",
    "bid",
    "proposal",
    "proposals",
    "quote",
    "procurement",
    "contract opportunity",
    "sources sought",
    "request for proposal",
    "request for quote",
}

DEADLINE_KEYWORDS = {
    "due date",
    "deadline",
    "responses due",
    "proposal due",
    "quotes due",
    "submission due",
}

SENDER_HINTS = {
    ".gov",
    "sam.gov",
    "procurement",
    "contracting",
    "acquisition",
    "solicitation",
}

NAICS_PATTERN = re.compile(r"\b(?:NAICS\s*(?:code)?[:#\-\s]*)?\d{6}\b", re.IGNORECASE)


def _join_message_text(message):
    attachment_names = " ".join(message.get("attachment_names") or [])
    return " ".join(
        str(value or "")
        for value in [
            message.get("sender"),
            message.get("from_email"),
            message.get("subject"),
            message.get("body_text"),
            attachment_names,
        ]
    ).lower()


def classify_contract_email(message):
    text = _join_message_text(message)
    reasons = []

    if any(hint in text for hint in SENDER_HINTS):
        reasons.append("sender/domain hint")

    if any(keyword in text for keyword in CONTRACT_KEYWORDS):
        reasons.append("contract keyword")

    if any(keyword in text for keyword in DEADLINE_KEYWORDS):
        reasons.append("deadline keyword")

    if NAICS_PATTERN.search(text):
        reasons.append("NAICS pattern")

    for attachment_name in message.get("attachment_names") or []:
        normalized_name = str(attachment_name or "").lower()
        if any(keyword in normalized_name for keyword in CONTRACT_KEYWORDS):
            reasons.append("attachment hint")
            break

    return {
        "is_candidate": len(reasons) >= 2 or "contract keyword" in reasons,
        "reasons": reasons,
    }


def is_contract_opportunity_email(message):
    return classify_contract_email(message)["is_candidate"]
