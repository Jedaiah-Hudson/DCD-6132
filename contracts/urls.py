from django.urls import path
from .view import (
    contract_detail,
    contract_notifications,
    contract_notifications_summary,
    contract_dropdown,
    contract_list,
    contract_notifications_bulk_update,
    contract_progress_detail,
    contract_progress_summary,
    generate_draft,
    sync_sam_opportunities,
)

urlpatterns = [
    path("api/contracts/", contract_list, name="contract-list"),
    path("api/contracts/<int:contract_id>/", contract_detail, name="contract-detail"),
    path("api/contracts/<int:contract_id>/progress/", contract_progress_detail, name="contract-progress-detail"),
    path("api/contract-progress/summary/", contract_progress_summary, name="contract-progress-summary"),
    path("api/notifications/", contract_notifications, name="contract-notifications"),
    path("api/notifications/summary/", contract_notifications_summary, name="contract-notifications-summary"),
    path("api/notifications/bulk-update/", contract_notifications_bulk_update, name="contract-notifications-bulk-update"),
    path("api/sam/sync/", sync_sam_opportunities, name="sam-sync"),
    path("contracts/dropdown/", contract_dropdown),
    path("generate-draft/", generate_draft, name="generate-draft"),
]
