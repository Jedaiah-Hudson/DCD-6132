import os
from datetime import datetime, timedelta

from contracts.management.services.procurement_ingest import ingest_procurement_record

SAM_OPPORTUNITIES_URL = "https://api.sam.gov/prod/opportunities/v2/search"


class SamApiError(Exception):
    status_code = 500

    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.status_code = status_code


def get_sam_api_key():
    api_key = os.environ.get("SAM_API_KEY")
    if not api_key:
        raise ValueError("SAM_API_KEY is not set in environment variables.")
    return api_key


def _build_sam_http_error_message(response):
    default_message = f"SAM.gov returned an HTTP error: {response.status_code}."

    try:
        payload = response.json()
    except ValueError:
        payload = None

    if response.status_code == 429:
        next_access_time = ""
        if isinstance(payload, dict):
            next_access_time = payload.get("nextAccessTime") or ""

        if next_access_time:
            cleaned_next_access_time = next_access_time.replace("+0000 UTC", " UTC").strip()
            return f"SAM.gov rate limit reached. Try again after {cleaned_next_access_time}."
        return "SAM.gov rate limit reached. Please try again later."

    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("description")
        if message:
            return f"SAM.gov request failed: {message}"

    return default_message


def fetch_sam_opportunities(
    notice_type=None,
    posted_from=None,
    posted_to=None,
    keyword=None,
    naics_code=None,
    limit=10,
    offset=0,
):
    import requests

    api_key = get_sam_api_key()

    # SAM requires postedFrom and postedTo in MM/dd/yyyy format
    if not posted_to:
        posted_to = datetime.today().strftime("%m/%d/%Y")

    if not posted_from:
        posted_from = (datetime.today() - timedelta(days=2)).strftime("%m/%d/%Y")

    params = {
        "api_key": api_key,
        "limit": limit,
        "offset": offset,
        "postedFrom": posted_from,
        "postedTo": posted_to,
    }

    if notice_type:
        params["noticeType"] = notice_type
    if keyword:
        params["keyword"] = keyword
    if naics_code:
        params["ncode"] = naics_code

    try:
        response = requests.get(SAM_OPPORTUNITIES_URL, params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise SamApiError("Request to SAM.gov timed out.")
    except requests.exceptions.ConnectionError:
        raise SamApiError("Could not connect to SAM.gov. Check internet, VPN, firewall, or endpoint URL.")
    except requests.exceptions.HTTPError as e:
        response = e.response
        if response is None:
            raise SamApiError("SAM.gov returned an HTTP error.")
        raise SamApiError(
            _build_sam_http_error_message(response),
            status_code=response.status_code,
        )
    except requests.exceptions.RequestException as e:
        raise SamApiError(f"SAM.gov request failed: {str(e)}")


import time

def ingest_sam_opportunities(
    notice_type=None,
    posted_from=None,
    posted_to=None,
    keyword=None,
    naics_code=None,
    limit=10,
    offset=0,
):
    total_ingested = 0
    batch_size = 2

    results = []
    raw_total_records = None

    while total_ingested < limit:
        payload = fetch_sam_opportunities(
            notice_type=notice_type,
            posted_from=posted_from,
            posted_to=posted_to,
            keyword=keyword,
            naics_code=naics_code,
            limit=batch_size,
            offset=offset,
        )

        if raw_total_records is None:
            raw_total_records = payload.get("totalRecords")

        records = (
            payload.get("opportunitiesData")
            or payload.get("opportunities")
            or payload.get("data")
            or []
        )

        if not records:
            break

        for record in records:
            contract, created = ingest_procurement_record(record, "sam")

            results.append({
                "id": contract.id,
                "title": contract.title,
                "source": contract.source,
                "created": created,
            })

            total_ingested += 1

            if total_ingested >= limit:
                break

        offset += batch_size

        time.sleep(3)

    return {
        "count_ingested": total_ingested,
        "results": results,
        "raw_total_records": raw_total_records,
    }
