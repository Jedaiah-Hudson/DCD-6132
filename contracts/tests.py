from io import StringIO
from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import CapabilityProfile, User
from contracts.management.services.procurement_ingest import normalize_procurement_record
from contracts.management.services.sam_api import SamApiError, fetch_sam_opportunities, ingest_sam_opportunities
from contracts.models import Contract, ContractNotification, DismissedContract, NAICSCode, UserContractProgress


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

    @patch("contracts.management.services.sam_api.ingest_procurement_record")
    @patch("contracts.management.services.sam_api.fetch_sam_opportunities")
    def test_ingest_sam_opportunities_uses_five_record_batches(self, mock_fetch, mock_ingest):
        records = [
            {
                "title": f"SAM Opportunity {index}",
                "description": f"Description {index}",
                "uiLink": f"https://sam.gov/{index}",
            }
            for index in range(10)
        ]
        mock_fetch.side_effect = [
            {
                "totalRecords": 10,
                "opportunitiesData": records[:5],
            },
            {
                "totalRecords": 10,
                "opportunitiesData": records[5:],
            },
        ]

        def ingest_record(record, source_name):
            contract = Contract.objects.create(
                source=Contract.SourceType.PROCUREMENT,
                title=record["title"],
                summary=record["description"],
                agency="SAM",
                hyperlink=record["uiLink"],
            )
            return contract, True

        mock_ingest.side_effect = ingest_record

        result = ingest_sam_opportunities(limit=10)

        self.assertEqual(result["count_ingested"], 10)
        self.assertEqual(mock_fetch.call_count, 2)
        self.assertEqual(mock_fetch.call_args_list[0].kwargs["limit"], 5)
        self.assertEqual(mock_fetch.call_args_list[0].kwargs["offset"], 0)
        self.assertEqual(mock_fetch.call_args_list[1].kwargs["limit"], 5)
        self.assertEqual(mock_fetch.call_args_list[1].kwargs["offset"], 5)

    @patch("contracts.management.services.sam_api.ingest_procurement_record")
    @patch("contracts.management.services.sam_api.fetch_sam_opportunities")
    def test_ingest_sam_opportunities_uses_one_partial_batch_for_small_limit(self, mock_fetch, mock_ingest):
        records = [
            {
                "title": f"SAM Opportunity {index}",
                "description": f"Description {index}",
                "uiLink": f"https://sam.gov/{index}",
            }
            for index in range(3)
        ]
        mock_fetch.return_value = {
            "totalRecords": 10,
            "opportunitiesData": records,
        }

        def ingest_record(record, source_name):
            contract = Contract.objects.create(
                source=Contract.SourceType.PROCUREMENT,
                title=record["title"],
                summary=record["description"],
                agency="SAM",
                hyperlink=record["uiLink"],
            )
            return contract, True

        mock_ingest.side_effect = ingest_record

        result = ingest_sam_opportunities(limit=3)

        self.assertEqual(result["count_ingested"], 3)
        mock_fetch.assert_called_once()
        self.assertEqual(mock_fetch.call_args.kwargs["limit"], 5)


class UserContractProgressApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="progress@example.com",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            email="other-progress@example.com",
            password="StrongPass123!",
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}
        self.contract = Contract.objects.create(
            source="procurement",
            title="Cloud Support",
            summary="Cloud support services.",
            agency="GSA",
            naics_code="541512",
            status="Active",
        )

    def test_summary_counts_only_current_users_tracked_progress(self):
        UserContractProgress.objects.create(
            user=self.user,
            contract=self.contract,
            contract_progress=UserContractProgress.ProgressChoices.WON,
        )
        other_contract = Contract.objects.create(
            source="procurement",
            title="Other Contract",
            summary="Other services.",
            agency="VA",
        )
        UserContractProgress.objects.create(
            user=self.other_user,
            contract=other_contract,
            contract_progress=UserContractProgress.ProgressChoices.LOST,
        )

        response = self.client.get("/api/contract-progress/summary/", **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["won"], 1)
        self.assertEqual(response.data["lost"], 0)
        self.assertEqual(response.data["pending"], 0)
        self.assertEqual(response.data["tracked"], 1)

    def test_get_progress_creates_default_user_progress_record(self):
        response = self.client.get(
            f"/api/contracts/{self.contract.id}/progress/",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["contract"], self.contract.id)
        self.assertEqual(response.data["contract_progress"], UserContractProgress.ProgressChoices.NONE)
        self.assertEqual(response.data["pursuit_role"], UserContractProgress.PursuitRoleChoices.UNDECIDED)
        self.assertEqual(response.data["notes"], "")

    def test_update_progress_pursuit_role_and_notes(self):
        response = self.client.patch(
            f"/api/contracts/{self.contract.id}/progress/",
            {
                "contract_progress": UserContractProgress.ProgressChoices.LOST,
                "pursuit_role": UserContractProgress.PursuitRoleChoices.SUBCONTRACTING,
                "notes": "No bid after review.",
            },
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["contract_progress"], UserContractProgress.ProgressChoices.LOST)
        self.assertEqual(response.data["pursuit_role"], UserContractProgress.PursuitRoleChoices.SUBCONTRACTING)
        self.assertEqual(response.data["notes"], "No bid after review.")

    def test_invalid_pursuit_role_is_rejected(self):
        response = self.client.patch(
            f"/api/contracts/{self.contract.id}/progress/",
            {"pursuit_role": "VENDOR"},
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_progress_value_is_rejected(self):
        response = self.client.patch(
            f"/api/contracts/{self.contract.id}/progress/",
            {"contract_progress": "MAYBE"},
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_summary_counts_workflow_only_contracts_as_tracked(self):
        UserContractProgress.objects.create(
            user=self.user,
            contract=self.contract,
            workflow_status=UserContractProgress.WorkflowChoices.REVIEWING,
        )

        response = self.client.get("/api/contract-progress/summary/", **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tracked"], 1)

    def test_progress_update_creates_notifications(self):
        response = self.client.patch(
            f"/api/contracts/{self.contract.id}/progress/",
            {
                "contract_progress": UserContractProgress.ProgressChoices.PENDING,
                "workflow_status": UserContractProgress.WorkflowChoices.DRAFTING,
            },
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            ContractNotification.objects.filter(
                user=self.user,
                contract=self.contract,
                notification_type=ContractNotification.NotificationType.PROGRESS,
            ).exists()
        )
        self.assertTrue(
            ContractNotification.objects.filter(
                user=self.user,
                contract=self.contract,
                notification_type=ContractNotification.NotificationType.WORKFLOW,
            ).exists()
        )

    def test_notifications_endpoint_returns_deadline_alerts_for_tracked_contracts(self):
        self.contract.deadline = timezone.now() + timedelta(days=5)
        self.contract.save(update_fields=["deadline"])
        UserContractProgress.objects.create(
            user=self.user,
            contract=self.contract,
            workflow_status=UserContractProgress.WorkflowChoices.REVIEWING,
        )

        response = self.client.get("/api/notifications/", **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["notifications"]), 1)
        self.assertGreaterEqual(response.data["unread_count"], 1)
        deadline_notifications = ContractNotification.objects.filter(
            user=self.user,
            contract=self.contract,
            notification_type=ContractNotification.NotificationType.DEADLINE,
        )
        self.assertEqual(deadline_notifications.count(), 1)
        self.assertEqual(
            deadline_notifications.first().unique_key,
            f"deadline:{self.contract.id}:5",
        )

    def test_bulk_update_marks_notifications_read_and_unread(self):
        notification = ContractNotification.objects.create(
            user=self.user,
            contract=self.contract,
            notification_type=ContractNotification.NotificationType.PROGRESS,
            severity=ContractNotification.SeverityChoices.INFO,
            unique_key="manual-progress",
            title="Progress updated",
            message="You moved Cloud Support to Pending.",
        )

        read_response = self.client.post(
            "/api/notifications/bulk-update/",
            {"notification_ids": [notification.id], "mark_as": "read"},
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

        unread_response = self.client.post(
            "/api/notifications/bulk-update/",
            {"notification_ids": [notification.id], "mark_as": "unread"},
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(unread_response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_bulk_update_deletes_notifications(self):
        notification = ContractNotification.objects.create(
            user=self.user,
            contract=self.contract,
            notification_type=ContractNotification.NotificationType.PROGRESS,
            severity=ContractNotification.SeverityChoices.INFO,
            unique_key="manual-delete",
            title="Progress updated",
            message="You moved Cloud Support to Pending.",
        )

        response = self.client.post(
            "/api/notifications/bulk-update/",
            {"notification_ids": [notification.id], "mark_as": "delete"},
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            ContractNotification.objects.filter(id=notification.id).exists()
        )

    def test_dismiss_contract_hides_it_and_clears_user_tracking(self):
        UserContractProgress.objects.create(
            user=self.user,
            contract=self.contract,
            contract_progress=UserContractProgress.ProgressChoices.PENDING,
        )
        ContractNotification.objects.create(
            user=self.user,
            contract=self.contract,
            notification_type=ContractNotification.NotificationType.PROGRESS,
            severity=ContractNotification.SeverityChoices.INFO,
            unique_key="manual-dismiss",
            title="Progress updated",
            message="You moved Cloud Support to Pending.",
        )

        response = self.client.delete(
            f"/api/contracts/{self.contract.id}/dismiss/",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            DismissedContract.objects.filter(user=self.user, contract=self.contract).exists()
        )
        self.assertFalse(
            UserContractProgress.objects.filter(user=self.user, contract=self.contract).exists()
        )
        self.assertFalse(
            ContractNotification.objects.filter(user=self.user, contract=self.contract).exists()
        )

    def test_dismissed_contract_detail_returns_not_found_for_same_user(self):
        DismissedContract.objects.create(user=self.user, contract=self.contract)

        response = self.client.get(
            f"/api/contracts/{self.contract.id}/",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_contract_detail_includes_matched_reasons_for_user_profile(self):
        naics_code = NAICSCode.objects.create(code="541512", title="Computer Systems Design Services")
        profile = CapabilityProfile.objects.create(user=self.user, company_name="Profile Co")
        profile.naics_codes.set([naics_code])

        response = self.client.get(
            f"/api/contracts/{self.contract.id}/",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("matched_reasons", response.data["contract"])
        self.assertTrue(
            any(
                "NAICS 541512 matches your capability profile" in reason
                for reason in response.data["contract"]["matched_reasons"]
            )
        )


class ContractListApiTests(APITestCase):
    def test_contract_list_filters_by_partner_case_insensitive(self):
        Contract.objects.create(
            source=Contract.SourceType.PROCUREMENT,
            title="Matched Partner Contract",
            summary="Matched partner summary.",
            agency="GSA",
            partner_name="Northwind Systems",
        )
        Contract.objects.create(
            source=Contract.SourceType.PROCUREMENT,
            title="Other Partner Contract",
            summary="Other partner summary.",
            agency="VA",
            partner_name="Atlas Facilities",
        )

        response = self.client.get("/api/contracts/?partner=northwind systems")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["contracts"]), 1)
        self.assertEqual(response.json()["contracts"][0]["title"], "Matched Partner Contract")
