from django.urls import path
from .view import contract_list, sync_sam_opportunities

urlpatterns = [
    path("api/contracts/", contract_list, name="contract-list"),
    path("api/sam/sync/", sync_sam_opportunities, name="sam-sync"),
]