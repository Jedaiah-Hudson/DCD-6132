import os
import requests
from datetime import datetime, timedelta

from contracts.management.services.procurement_ingest import ingest_procurement_record

SAM_OPPORTUNITIES_URL = "https://api.sam.gov/prod/opportunities/v2/search"


def get_sam_api_key():
    api_key = os.environ.get("SAM_API_KEY")
    if not api_key:
        raise ValueError("SAM_API_KEY is not set in environment variables.")
    return api_key


def fetch_sam_opportunities(
    notice_type=None,
    posted_from=None,
    posted_to=None,
    keyword=None,
    naics_code=None,
    limit=10,
    offset=0,
):
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
        raise Exception("Request to SAM.gov timed out.")
    except requests.exceptions.ConnectionError:
        raise Exception("Could not connect to SAM.gov. Check internet, VPN, firewall, or endpoint URL.")
    except requests.exceptions.HTTPError as e:
        raise Exception(f"SAM.gov returned an HTTP error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"SAM.gov request failed: {str(e)}")


import time

def ingest_sam_opportunities(
    notice_type=None,
    posted_from=None,
    posted_to=None,
    keyword=None,
    naics_code=None,
    limit=10,   
):
    total_ingested = 0
    offset = 0
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