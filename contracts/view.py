from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from contracts.management.services.naics_utils import get_category_for_naics
from contracts.models import Contract, UserContractProgress
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from contracts.management.services.sam_api import SamApiError, ingest_sam_opportunities
from contracts.serializer import UserContractProgressSerializer


@csrf_exempt
@require_POST
def sync_sam_opportunities(request):
    try:
        body = json.loads(request.body or "{}")
        limit = body.get("limit", 10)  # default safe limit

        result = ingest_sam_opportunities(limit=limit)

        return JsonResponse({
            "status": "success",
            "result": result
        })

    except SamApiError as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=e.status_code)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
    
def contract_list(request):
    contracts = Contract.objects.all().order_by("deadline")

    source = request.GET.get("source")
    if source:
        contracts = contracts.filter(source=source)

    data = []

    for contract in contracts:
        category = get_category_for_naics(contract.naics_code)

        if category and contract.category != category:
            contract.category = category
            contract.save(update_fields=["category"])

        data.append({
            "id": contract.id,
            "source": contract.source,
            "title": contract.title,
            "summary": contract.summary,
            "agency": contract.agency,
            "sub_agency": contract.sub_agency,
            "naics_code": contract.naics_code,
            "category": category,
            "deadline": contract.deadline.isoformat() if contract.deadline else None,
            "hyperlink": contract.hyperlink,
            "partner_name": contract.partner_name,
            "status": contract.status,
        })

    return JsonResponse({"contracts": data})


def _serialize_contract(contract):
    return {
        "id": contract.id,
        "source": contract.source,
        "procurement_portal": contract.procurement_portal,
        "title": contract.title,
        "summary": contract.summary,
        "agency": contract.agency,
        "sub_agency": contract.sub_agency,
        "naics_code": contract.naics_code,
        "category": contract.category,
        "deadline": contract.deadline.isoformat() if contract.deadline else None,
        "hyperlink": contract.hyperlink,
        "partner_name": contract.partner_name,
        "status": contract.status,
        "created_at": contract.created_at.isoformat() if contract.created_at else None,
        "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def contract_progress_summary(request):
    counts = {
        UserContractProgress.ProgressChoices.WON: 0,
        UserContractProgress.ProgressChoices.LOST: 0,
        UserContractProgress.ProgressChoices.PENDING: 0,
    }

    progress_counts = (
        UserContractProgress.objects
        .filter(user=request.user)
        .exclude(contract_progress=UserContractProgress.ProgressChoices.NONE)
        .values("contract_progress")
        .annotate(total=Count("id"))
    )

    for item in progress_counts:
        counts[item["contract_progress"]] = item["total"]

    tracked = sum(counts.values())
    return Response(
        {
            "won": counts[UserContractProgress.ProgressChoices.WON],
            "lost": counts[UserContractProgress.ProgressChoices.LOST],
            "pending": counts[UserContractProgress.ProgressChoices.PENDING],
            "tracked": tracked,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def contract_detail(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    return Response({"contract": _serialize_contract(contract)}, status=status.HTTP_200_OK)


@api_view(["GET", "POST", "PATCH"])
@permission_classes([IsAuthenticated])
def contract_progress_detail(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    progress, _created = UserContractProgress.objects.get_or_create(
        user=request.user,
        contract=contract,
    )

    if request.method == "GET":
        serializer = UserContractProgressSerializer(progress)
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = UserContractProgressSerializer(
        progress,
        data=request.data,
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data, status=status.HTTP_200_OK)
