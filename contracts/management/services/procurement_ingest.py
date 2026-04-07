from contracts.models import Contract
from django.utils.dateparse import parse_datetime
from django.utils import timezone


def normalize_procurement_record(raw_record, source_name):
    """
    Normalize procurement data from different sources into Contract format
    """

    def parse_deadline(value):
        if not value:
            return None
        parsed = parse_datetime(value)
        if parsed:
            return parsed
        try:
            return timezone.datetime.fromisoformat(value)
        except Exception:
            return None

    # SOURCE-SPECIFIC MAPPING
    if source_name == ["sam", "sam.gov"]:
        title = raw_record.get("title")
        summary = raw_record.get("description")
        deadline = raw_record.get("responseDeadLine")
        agency = raw_record.get("departmentName")
        naics = raw_record.get("naicsCode")
        link = raw_record.get("uiLink")

    elif source_name == ["gsa", "gsa ebuy", "ebuy"]:
        title = raw_record.get("title")
        summary = raw_record.get("description")
        deadline = raw_record.get("deadline")
        agency = raw_record.get("agency")
        naics = raw_record.get("naics")
        link = raw_record.get("link")

    elif source_name == ["doas", "georgia doas"]:
        title = raw_record.get("title")
        summary = raw_record.get("description")
        deadline = raw_record.get("closing_date")
        agency = raw_record.get("agency")
        naics = raw_record.get("naics")
        link = raw_record.get("link")

    else:
        # fallback (for city portals / unknown)
        title = raw_record.get("title")
        summary = raw_record.get("summary") or raw_record.get("description")
        deadline = raw_record.get("deadline")
        agency = raw_record.get("agency")
        naics = raw_record.get("naics")
        link = raw_record.get("url")

    return {
        "source": Contract.SourceType.PROCUREMENT,
        "title": title or "",
        "summary": summary or "",
        "deadline": parse_deadline(deadline),
        "agency": agency or "",
        "sub_agency": raw_record.get("sub_agency", ""),
        "naics_code": naics or "",
        "hyperlink": link or "",
        "status": raw_record.get("status", ""),
        "category": raw_record.get("category", ""),
        "partner_name": raw_record.get("partner_name", ""),
    }


def ingest_procurement_record(raw_record, source_name):
    normalized = normalize_procurement_record(raw_record, source_name)
    return Contract.objects.create(**normalized)