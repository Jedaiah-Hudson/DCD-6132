import re
from datetime import datetime

from django.utils import timezone

from contracts.management.services.naics_utils import get_category_for_naics
from contracts.models import Contract


NAICS_RE = re.compile(r"\b(?:NAICS\s*(?:code)?[:#\-\s]*)?(\d{6})\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s<>)\"']+")
FIELD_RE_TEMPLATE = r"^\s*{label}\s*[:\-]\s*(?P<value>.+?)\s*$"
DATE_PATTERNS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
]
DEADLINE_RE = re.compile(
    r"(?:due date|deadline|responses due|proposal due|quotes due|submission due)\s*[:\-]?\s*"
    r"(?P<date>[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def _clean_subject(subject):
    cleaned = re.sub(r"^\s*(re|fw|fwd)\s*:\s*", "", subject or "", flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^\s*(rfp|rfq|rfi|solicitation|bid opportunity|contract opportunity)\s*[:\-]\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def _extract_labeled_value(text, labels):
    for label in labels:
        pattern = re.compile(
            FIELD_RE_TEMPLATE.format(label=re.escape(label)),
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text or "")
        if match:
            return match.group("value").strip()
    return ""


def _parse_deadline(text):
    match = DEADLINE_RE.search(text or "")
    if not match:
        return None

    raw_date = match.group("date").replace(",", "").strip()
    candidates = [raw_date]
    if re.match(r"^[A-Za-z]", raw_date):
        parts = raw_date.split()
        if len(parts) == 3:
            candidates.append(f"{parts[0]} {parts[1]}, {parts[2]}")

    for candidate in candidates:
        for date_pattern in DATE_PATTERNS:
            try:
                parsed = datetime.strptime(candidate, date_pattern)
            except ValueError:
                continue
            return timezone.make_aware(parsed, timezone.get_current_timezone())

    return None


def _summary_from_body(body):
    compact = re.sub(r"\s+", " ", body or "").strip()
    if not compact:
        return "No description provided"
    return compact[:1000]


def parse_contract_from_email(message, mailbox_connection=None):
    body = message.get("body_text") or ""
    subject = message.get("subject") or ""
    text = f"{subject}\n{body}"

    naics_match = NAICS_RE.search(text)
    naics_code = naics_match.group(1) if naics_match else ""
    hyperlink_match = URL_RE.search(text)
    agency = _extract_labeled_value(text, ["Agency", "Department", "Buyer"])
    sub_agency = _extract_labeled_value(text, ["Sub-agency", "Sub Agency", "Office"])
    title = (
        _extract_labeled_value(text, ["Title", "Opportunity", "Solicitation"])
        or _clean_subject(subject)
        or "Email Contract Opportunity"
    )

    provider = getattr(mailbox_connection, "provider", "") or message.get("provider") or ""
    source = Contract.SourceType.GMAIL if provider == "gmail" else Contract.SourceType.OUTLOOK

    return {
        "source": source,
        "procurement_portal": "",
        "title": title[:255],
        "summary": _summary_from_body(body),
        "deadline": _parse_deadline(text),
        "agency": agency[:255] if agency else "",
        "sub_agency": sub_agency[:255] if sub_agency else "",
        "naics_code": naics_code,
        "hyperlink": hyperlink_match.group(0).rstrip(".,") if hyperlink_match else "",
        "partner_name": (message.get("sender") or message.get("from_email") or "")[:255],
        "status": "Active",
        "category": get_category_for_naics(naics_code) if naics_code else "",
    }
