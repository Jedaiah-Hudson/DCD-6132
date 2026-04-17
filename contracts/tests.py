from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from contracts.management.services.procurement_ingest import normalize_procurement_record
from contracts.management.services.sam_api import SamApiError, fetch_sam_opportunities


class ProcurementIngestTests(TestCase):
    @patch(
        "contracts.management.services.procurement_ingest.fetch_description_text",
        return_value="Detailed procurement notice",
    )
    def test_normalize_sam_record_uses_sam_field_mapping(self, _fetch_description_text):
        record = {
            "title": "SAM Opportunity",
            "description": "https://sam.gov/notice/123",
            "responseDeadLine": "2026-04-08T12:00:00",
            "fullParentPathName": "Department of Energy.Office of Science",
            "naicsCode": "541512",
            "uiLink": "https://sam.gov/example",
            "active": "Yes",
            "pointOfContact": [{"fullName": "Alex Buyer"}],
        }

        normalized = normalize_procurement_record(record, "sam")

        self.assertEqual(normalized["title"], "SAM Opportunity")
        self.assertEqual(normalized["summary"], "Detailed procurement notice")
        self.assertEqual(normalized["agency"], "Department of Energy")
        self.assertEqual(normalized["sub_agency"], "Office of Science")
        self.assertEqual(normalized["naics_code"], "541512")
        self.assertEqual(normalized["hyperlink"], "https://sam.gov/example")
        self.assertEqual(normalized["status"], "Active")
        self.assertEqual(normalized["partner_name"], "Alex Buyer")
        self.assertEqual(normalized["procurement_portal"], "SAM.gov")


class IngestSamOpportunitiesCommandTests(TestCase):
    @patch("contracts.management.services.sam_api.ingest_sam_opportunities")
    def test_command_calls_service_and_prints_summary(self, mock_ingest):
        mock_ingest.return_value = {
            "count_ingested": 1,
            "count_created": 1,
            "count_updated": 0,
            "raw_total_records": 10,
            "results": [
                {
                    "id": 42,
                    "title": "Cloud Migration Support",
                    "agency": "Department of Energy",
                    "created": True,
                }
            ],
        }
        stdout = StringIO()

        call_command(
            "ingest_sam_opportunities",
            keyword="cloud",
            naics_code="541512",
            limit=5,
            stdout=stdout,
        )

        mock_ingest.assert_called_once_with(
            notice_type=None,
            posted_from=None,
            posted_to=None,
            keyword="cloud",
            naics_code="541512",
            limit=5,
            offset=0,
        )
        output = stdout.getvalue()
        self.assertIn("Ingested 1 opportunities from SAM.gov.", output)
        self.assertIn("Created: 1", output)
        self.assertIn("Updated: 0", output)
        self.assertIn("SAM total records reported: 10", output)
        self.assertIn("[created] #42 Cloud Migration Support (Department of Energy)", output)


class SamApiErrorHandlingTests(TestCase):
    @patch("contracts.management.services.sam_api.get_sam_api_key", return_value="test-key")
    @patch("requests.get")
    def test_fetch_sam_opportunities_formats_rate_limit_error(self, mock_get, _get_sam_api_key):
        import requests

        response = requests.Response()
        response.status_code = 429
        response._content = (
            b'{"code":"900804","message":"Message throttled out","description":"You have exceeded your quota.",'
            b'"nextAccessTime":"2026-Apr-17 00:00:00+0000 UTC"}'
        )
        response.url = "https://api.sam.gov/prod/opportunities/v2/search"

        http_error = requests.exceptions.HTTPError(response=response)
        mock_response = mock_get.return_value
        mock_response.raise_for_status.side_effect = http_error
        mock_response.json.return_value = {
            "code": "900804",
            "message": "Message throttled out",
            "description": "You have exceeded your quota.",
            "nextAccessTime": "2026-Apr-17 00:00:00+0000 UTC",
        }

        with self.assertRaises(SamApiError) as exc:
            fetch_sam_opportunities(limit=1)

        self.assertEqual(exc.exception.status_code, 429)
        self.assertEqual(
            str(exc.exception),
            "SAM.gov rate limit reached. Try again after 2026-Apr-17 00:00:00 UTC.",
        )
