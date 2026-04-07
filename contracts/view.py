from django.http import JsonResponse
from contracts.services.naics_utils import get_category_for_naics
from contracts.models import Contract


def contract_list(request):
    contracts = Contract.objects.filter(user=request.user).order_by("deadline")
    
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