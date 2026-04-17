from django.http import JsonResponse
from contracts.management.services.naics_utils import get_category_for_naics
from contracts.models import Contract
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from contracts.management.services.sam_api import SamApiError, ingest_sam_opportunities


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
