import os

from contracts.models import Contract
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from contracts.management.services.naics_utils import get_category_for_naics
import re
import html
import requests



def normalize_procurement_record(raw_record, source_name):
    """
    Normalize procurement data from different sources into Contract format
    """

    def parse_deadline(value):
        if not value:
            return None

        dt = parse_datetime(value)

        if not dt:
            try:
                dt = timezone.datetime.fromisoformat(value)
            except Exception:
                return None
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())

        return dt
        
    source_name = (source_name or "").strip().lower()


    if "sam" in source_name:
        title = raw_record.get("title")
        procurement_portal = "SAM.gov"

        summary_url = raw_record.get("description")

        summary = fetch_description_text(summary_url)
        if not summary:
            summary = "No description Provided"

        deadline = raw_record.get("responseDeadLine")

        full_path = raw_record.get("fullParentPathName", "")

        agency = ""
        sub_agency = ""

        if full_path:
            parts = full_path.split(".")
            agency = parts[0] if len(parts) > 0 else ""
            sub_agency = parts[-1] if len(parts) > 1 else ""

        naics = raw_record.get("naicsCode")

        link = raw_record.get("uiLink")

        status_raw = raw_record.get("active")

        if status_raw == "Yes":
            status = "Active"
        elif status_raw == "No":
            status = "Inactive"
        else:
            status = "Unknown"

    
        contacts = raw_record.get("pointOfContact", [])
        partner_name = contacts[0]["fullName"] if contacts else ""
        category = get_category_for_naics(naics) if naics else ""
    

    return {
        "source": Contract.SourceType.PROCUREMENT,
        "title": title or "",
        "summary": summary or "",
        "deadline": parse_deadline(deadline),
        "agency": agency or "",
        "sub_agency": sub_agency or "",
        "naics_code": naics or "",
        "hyperlink": link or "",
        "partner_name": partner_name or "",
        "status": status or "",
        "category": category or "",
        "procurement_portal": procurement_portal,
    }


def ingest_procurement_record(raw_record, source_name):
    normalized = normalize_procurement_record(raw_record, source_name)

   
    deadline = normalized.get("deadline")
    if deadline and timezone.is_naive(deadline):
        normalized["deadline"] = timezone.make_aware(deadline, timezone.get_current_timezone())


    hyperlink = normalized.get("hyperlink")
    title = normalized.get("title")
    agency = normalized.get("agency")

    if hyperlink:
        contract, created = Contract.objects.update_or_create(
            hyperlink=hyperlink,
            defaults=normalized,
        )
        return contract, created


    contract, created = Contract.objects.update_or_create(
        source=Contract.SourceType.PROCUREMENT,
        title=title,
        agency=agency,
        deadline=normalized.get("deadline"),  
        defaults=normalized,
    )

    return contract, created

SAM_API_KEY = os.environ.get("SAM_API_KEY")


def fetch_description_text(url):
    if not url:
        return ""

    try:
        response = requests.get(
            url,
            params={"api_key": SAM_API_KEY},
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        description = (
            data.get("description")
            or data.get("body")
            or data.get("noticeDescription")
            or ""
        )

        # Decode HTML entities
        description = html.unescape(description)

        # Strip HTML tags
        description = re.sub(r"<[^>]+>", "", description)

        # Normalize whitespace
        description = re.sub(r"\s+", " ", description).strip()

        return description

    except Exception as e:
        print("DESC FETCH ERROR:", e)
        return ""
