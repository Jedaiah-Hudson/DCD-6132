from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from contracts.management.services.naics_utils import get_category_for_naics
from contracts.models import Contract, ContractNotification, DismissedContract, UserContractProgress
from accounts.models import CapabilityProfile, MailboxContract
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from contracts.management.services.sam_api import SamApiError, ingest_sam_opportunities
from contracts.serializer import ContractNotificationSerializer, UserContractProgressSerializer


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

    partner = (request.GET.get("partner") or "").strip()
    if partner:
        contracts = contracts.filter(partner_name__iexact=partner)

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


def _build_contract_matched_reasons(contract, user):
    reasons = []

    profile = CapabilityProfile.objects.filter(user=user).first()
    if profile and contract.naics_code:
        matching_naics = profile.naics_codes.filter(code=contract.naics_code).first()
        if matching_naics:
            reasons.append(
                f"NAICS {matching_naics.code} matches your capability profile ({matching_naics.title})"
            )

    mailbox_matches = MailboxContract.objects.filter(
        user=user,
        contract=contract,
    ).exclude(matched_terms="")
    for match in mailbox_matches:
        reasons.append(f"Mailbox keywords matched: {match.matched_terms}")

    return reasons


def _serialize_contract(contract, user=None):
    data = {
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
    if user and user.is_authenticated:
        data["matched_reasons"] = _build_contract_matched_reasons(contract, user)
    return data

from django.http import JsonResponse
from .models import Contract


def contract_dropdown(request):
    contracts = Contract.objects.all().order_by("-deadline")

    data = [
        {
            "id": c.id,
            "title": c.title,
        }
        for c in contracts
    ]

    return JsonResponse({"contracts": data})
# views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Contract
DEADLINE_NOTIFICATION_THRESHOLDS = [
    (14, "2 weeks", ContractNotification.SeverityChoices.LOW),
    (7, "1 week", ContractNotification.SeverityChoices.MEDIUM),
    (5, "5 days", ContractNotification.SeverityChoices.MEDIUM),
    (3, "3 days", ContractNotification.SeverityChoices.HIGH),
    (1, "1 day", ContractNotification.SeverityChoices.HIGH),
]


def _tracked_progress_queryset(user):
    return (
        UserContractProgress.objects
        .filter(user=user)
        .filter(
            Q(contract_progress__in=[
                UserContractProgress.ProgressChoices.PENDING,
                UserContractProgress.ProgressChoices.WON,
                UserContractProgress.ProgressChoices.LOST,
            ])
            | Q(workflow_status__in=[
                UserContractProgress.WorkflowChoices.REVIEWING,
                UserContractProgress.WorkflowChoices.DRAFTING,
                UserContractProgress.WorkflowChoices.SUBMITTED,
            ])
            | Q(relationship_label__in=[
                UserContractProgress.RelationshipChoices.PRIME,
                UserContractProgress.RelationshipChoices.SUBCONTRACTOR,
                UserContractProgress.RelationshipChoices.TEAMING,
                UserContractProgress.RelationshipChoices.VENDOR,
                UserContractProgress.RelationshipChoices.CONSULTANT,
            ])
        )
        .select_related("contract")
    )


def _create_notification(user, contract, notification_type, unique_key, title, message, severity, due_at=None):
    ContractNotification.objects.get_or_create(
        user=user,
        unique_key=unique_key,
        defaults={
            "contract": contract,
            "notification_type": notification_type,
            "severity": severity,
            "title": title,
            "message": message,
            "due_at": due_at,
        },
    )


def _sync_contract_notifications_for_user(user):
    now = timezone.now()

    for progress in _tracked_progress_queryset(user):
        contract = progress.contract
        deadline_notifications = ContractNotification.objects.filter(
            user=user,
            contract=contract,
            notification_type=ContractNotification.NotificationType.DEADLINE,
        )

        if contract.deadline and contract.deadline >= now:
            days_remaining = (contract.deadline.date() - now.date()).days
            matching_threshold = next(
                (
                    (threshold_days, threshold_label, severity)
                    for threshold_days, threshold_label, severity in sorted(
                        DEADLINE_NOTIFICATION_THRESHOLDS,
                        key=lambda item: item[0],
                    )
                    if days_remaining <= threshold_days
                ),
                None,
            )

            active_deadline_key = None
            if matching_threshold:
                threshold_days, threshold_label, severity = matching_threshold
                active_deadline_key = f"deadline:{contract.id}:{threshold_days}"
                _create_notification(
                    user=user,
                    contract=contract,
                    notification_type=ContractNotification.NotificationType.DEADLINE,
                    unique_key=active_deadline_key,
                    title="Deadline approaching",
                    message=f"{contract.title} is due in {threshold_label}.",
                    severity=severity,
                    due_at=contract.deadline,
                )

            if active_deadline_key:
                deadline_notifications.exclude(unique_key=active_deadline_key).delete()
            else:
                deadline_notifications.delete()
        else:
            deadline_notifications.delete()

        if contract.status and contract.status.lower() != "active":
            _create_notification(
                user=user,
                contract=contract,
                notification_type=ContractNotification.NotificationType.STATUS,
                unique_key=f"status:{contract.id}:{contract.status.lower()}",
                title="Contract status changed",
                message=f"{contract.title} is no longer active. Current status: {contract.status}.",
                severity=ContractNotification.SeverityChoices.HIGH,
                due_at=contract.deadline,
            )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_draft(request):
    from .management.services.openai_service import generate_rfp_response
    from .management.services.prompt_builder import build_capability_profile_text

    user = request.user
    contract_id = request.data.get("contract_id")

    # 1. Get contract
    contract = get_object_or_404(Contract, id=contract_id)

    # 2. Get user's capability profile (latest one)
    profile = CapabilityProfile.objects.filter(user=user).order_by("-updated_at").first()

    if not profile:
        return Response({"error": "No capability profile found"}, status=400)

    # 3. Convert profile → clean text
    capability_text = build_capability_profile_text(profile)

    # 4. Generate AI response
    ai_output = generate_rfp_response(
        contract_text = f"""
            Contract Title: {contract.title}
            Agency: {contract.agency}
            Sub-agency: {contract.sub_agency}
            Summary: {contract.summary}
            NAICS Code: {contract.naics_code}
            Deadline: {contract.deadline}
            """,
        capability_text=capability_text
    )
    

    # 5. Return only (no saving)
    return Response({
        "contract_title": contract.title,
        "generated_text": ai_output
    })

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
        .filter(
            user=request.user,
            contract_progress__in=[
                UserContractProgress.ProgressChoices.WON,
                UserContractProgress.ProgressChoices.LOST,
                UserContractProgress.ProgressChoices.PENDING,
            ],
        )
        .values("contract_progress")
        .annotate(total=Count("id"))
    )

    for item in progress_counts:
        counts[item["contract_progress"]] = item["total"]

    tracked = _tracked_progress_queryset(request.user).count()
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
    contract = get_object_or_404(
        Contract.objects.exclude(dismissals__user=request.user),
        id=contract_id,
    )
    return Response({"contract": _serialize_contract(contract, request.user)}, status=status.HTTP_200_OK)


@api_view(["DELETE", "POST"])
@permission_classes([IsAuthenticated])
def dismiss_contract(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    reason = (request.data.get("reason") or "not_interested").strip() or "not_interested"

    DismissedContract.objects.get_or_create(
        user=request.user,
        contract=contract,
        defaults={"reason": reason},
    )

    UserContractProgress.objects.filter(user=request.user, contract=contract).delete()
    ContractNotification.objects.filter(user=request.user, contract=contract).delete()

    return Response(
        {
            "detail": "Contract removed from your recommendations.",
            "contract_id": contract.id,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def contract_notifications_summary(request):
    _sync_contract_notifications_for_user(request.user)

    unread_count = ContractNotification.objects.filter(
        user=request.user,
        is_read=False,
    ).count()

    return Response(
        {"unread_count": unread_count},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def contract_notifications(request):
    _sync_contract_notifications_for_user(request.user)

    notifications = ContractNotification.objects.filter(user=request.user).select_related("contract")
    serializer = ContractNotificationSerializer(notifications, many=True)

    unread_count = notifications.filter(is_read=False).count()
    return Response(
        {
            "notifications": serializer.data,
            "unread_count": unread_count,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def contract_notifications_bulk_update(request):
    notification_ids = request.data.get("notification_ids") or []
    mark_as = (request.data.get("mark_as") or "").strip().lower()

    if mark_as not in {"read", "unread", "delete"}:
        return Response(
            {"detail": "mark_as must be read, unread, or delete."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(notification_ids, list) or not notification_ids:
        return Response(
            {"detail": "notification_ids must be a non-empty list."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    notifications = ContractNotification.objects.filter(
        user=request.user,
        id__in=notification_ids,
    )

    if mark_as == "delete":
        deleted_count, _ = notifications.delete()
        return Response(
            {
                "updated_count": deleted_count,
                "mark_as": mark_as,
            },
            status=status.HTTP_200_OK,
        )

    is_read = mark_as == "read"
    updated_count = notifications.update(is_read=is_read, updated_at=timezone.now())

    return Response(
        {
            "updated_count": updated_count,
            "mark_as": mark_as,
        },
        status=status.HTTP_200_OK,
    )


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

    previous_progress = progress.contract_progress
    previous_workflow = progress.workflow_status

    serializer = UserContractProgressSerializer(
        progress,
        data=request.data,
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    progress.refresh_from_db()

    if progress.contract_progress != previous_progress:
        progress_label = progress.get_contract_progress_display()
        ContractNotification.objects.create(
            user=request.user,
            contract=contract,
            notification_type=ContractNotification.NotificationType.PROGRESS,
            severity=ContractNotification.SeverityChoices.INFO,
            unique_key=f"progress:{contract.id}:{timezone.now().isoformat()}",
            title="Progress updated",
            message=f"You moved {contract.title} to {progress_label}.",
            due_at=contract.deadline,
        )

    if progress.workflow_status != previous_workflow:
        workflow_label = progress.get_workflow_status_display()
        ContractNotification.objects.create(
            user=request.user,
            contract=contract,
            notification_type=ContractNotification.NotificationType.WORKFLOW,
            severity=ContractNotification.SeverityChoices.INFO,
            unique_key=f"workflow:{contract.id}:{timezone.now().isoformat()}",
            title="Workflow updated",
            message=f"You moved {contract.title} to the {workflow_label} stage.",
            due_at=contract.deadline,
        )

    _sync_contract_notifications_for_user(request.user)

    return Response(serializer.data, status=status.HTTP_200_OK)
