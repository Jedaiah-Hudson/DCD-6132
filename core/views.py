from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import json
import re
import pytesseract
from django.db.models import Q

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from accounts.models import CapabilityProfile, User
from accounts.profile_options import MATCHMAKING_OPTION_FIELDS
from contracts.models import Contract, NAICSCode, UserContractProgress
from contracts.management.services.naics_utils import get_category_for_naics
from core.services.capability_extraction import (
    extract_text_from_capability_document,
    is_supported_capability_document,
    parse_capability_text,
)
from core.services.matchmaking import get_matched_contracts_for_user
from .forms import CapabilityProfileForm
from .serializers import OpportunitySerializer

# Create your views here.
@login_required(login_url='/accounts/login-vis/')
def dashboard(request):
    template_data = {'title': 'Dashboard'}
    return render(request, 'core/dashboard.html', {'template_data': template_data})


@login_required(login_url='/accounts/login-vis/')
def notifications(request):
    template_data = {'title': 'Notifications'}
    return render(request, 'core/notifications.html', {'template_data': template_data})


PROFILE_KEYS = [
    'company_name',
    'capability_summary',
    'core_competencies',
    'differentiators',
    'naics_codes',
    'certifications',
    'past_performance',
    'contact_name',
    'contact_email',
    'contact_phone',
    'website',
]

MATCHMAKING_PROFILE_KEYS = list(MATCHMAKING_OPTION_FIELDS.keys())

SUPPORTED_DOCUMENT_MESSAGE = 'Please upload a PDF, PNG, JPG, or JPEG file.'


def normalize_profile_option_list(value, allowed_options):
    if value is None:
        return []

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        return []

    allowed_lookup = {option.lower(): option for option in allowed_options}
    normalized_values = []
    for raw_value in values:
        normalized_key = str(raw_value or '').strip().lower()
        allowed_value = allowed_lookup.get(normalized_key)
        if allowed_value and allowed_value not in normalized_values:
            normalized_values.append(allowed_value)

    return normalized_values


def normalize_contract_status(value):
    normalized = (value or '').strip().lower()

    if normalized in {'yes', 'active'}:
        return 'Active'

    if normalized in {'no', 'inactive'}:
        return 'Inactive'

    if normalized:
        return value

    return ''


def extract_text_from_pdf(uploaded_file):
    return extract_text_from_capability_document(uploaded_file)

@login_required(login_url='/accounts/login-vis/')
def profile(request):
    template_data = {'title': 'Profile'}
    profile_form = CapabilityProfileForm()
    structured_data = {key: '' for key in PROFILE_KEYS}
    extracted_text = None
    ocr_error = None
    submitted_data = None
    processed_file_name = None
    success_message = None
    existing_profile = CapabilityProfile.objects.filter(user=request.user).first()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'extract_ocr':
            uploaded_file = request.FILES.get('capability_pdf')

            # start fresh for every uploaded document
            structured_data = {key: '' for key in PROFILE_KEYS}
            submitted_data = None

            if not uploaded_file:
                profile_form = CapabilityProfileForm(request.POST, request.FILES)
                profile_form.add_error('capability_pdf', 'Upload a capability statement document to extract.')
            elif not is_supported_capability_document(uploaded_file):
                profile_form = CapabilityProfileForm(request.POST, request.FILES)
                profile_form.add_error('capability_pdf', SUPPORTED_DOCUMENT_MESSAGE)
            else:
                try:
                    processed_file_name = uploaded_file.name
                    extracted_text = extract_text_from_capability_document(uploaded_file)
                    parsed_data = parse_capability_text(extracted_text)

                    structured_data.update(parsed_data)
                    profile_form = CapabilityProfileForm(initial=structured_data)

                except pytesseract.TesseractNotFoundError:
                    ocr_error = 'Tesseract is not installed or not in your PATH.'
                    profile_form = CapabilityProfileForm()
                except Exception as exc:
                    ocr_error = f'Failed to process document: {exc}'
                    profile_form = CapabilityProfileForm()

        elif action == 'submit_profile':
                profile_form = CapabilityProfileForm(request.POST, request.FILES)

                if profile_form.is_valid():
                    capability_profile, created = CapabilityProfile.objects.get_or_create(
                        user=request.user
                    )

                    for key in PROFILE_KEYS:
                        setattr(capability_profile, key, profile_form.cleaned_data.get(key, ''))

                    uploaded_file = request.FILES.get('capability_pdf')
                    if uploaded_file:
                        if hasattr(capability_profile, 'source_pdf'):
                            capability_profile.source_pdf = uploaded_file
                        capability_profile.is_ocr_generated = True
                        try:
                            extracted_text = extract_text_from_capability_document(uploaded_file)
                            capability_profile.ocr_extracted_text = extracted_text
                        except Exception:
                            pass

                    capability_profile.is_approved = True
                    capability_profile.save()

                    success_message = 'Capability profile saved successfully.'
                    structured_data = {key: getattr(capability_profile, key, '') for key in PROFILE_KEYS}
                    profile_form = CapabilityProfileForm(initial=structured_data)
                else:
                    structured_data = {
                        key: request.POST.get(key, '')
                        for key in PROFILE_KEYS
                    }

    else:
        if existing_profile:
            initial_data = {key: getattr(existing_profile, key, '') for key in PROFILE_KEYS}
            profile_form = CapabilityProfileForm(initial=initial_data)
        else:
            profile_form = CapabilityProfileForm()


    return render(
        request,
        'core/profile.html',
        {
            'template_data': template_data,
            'profile_form': profile_form,
            'structured_data': structured_data,
            'structured_data_json': json.dumps(structured_data, indent=2),
            'extracted_text': extracted_text,
            'ocr_error': ocr_error,
            'submitted_data': submitted_data,
            'processed_file_name': processed_file_name,
            'editing': bool(existing_profile),
            'success_message': success_message,
        },
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_capability_profile(request):

    capability_data = {
        key: request.data.get(key, '')
        for key in PROFILE_KEYS
    }
    for key, allowed_options in MATCHMAKING_OPTION_FIELDS.items():
        capability_data[key] = normalize_profile_option_list(
            request.data.get(key),
            allowed_options,
        )

    # remove many-to-many field first
    naics_codes = capability_data.pop("naics_codes", [])

    profile, created = CapabilityProfile.objects.update_or_create(
        user=request.user,
        defaults=capability_data
    )

    # save dropdown selections
    if naics_codes:
        if isinstance(naics_codes, str):
            naics_codes = re.findall(r"\b\d{6}\b", naics_codes)

        normalized_naics_codes = []
        for code in naics_codes:
            normalized_code = str(code or "").strip()
            if re.fullmatch(r"\d{6}", normalized_code) and normalized_code not in normalized_naics_codes:
                normalized_naics_codes.append(normalized_code)

        for code in normalized_naics_codes:
            NAICSCode.objects.get_or_create(
                code=code,
                defaults={"title": "Imported from capability profile"},
            )

        naics_objects = NAICSCode.objects.filter(code__in=normalized_naics_codes)
        profile.naics_codes.set(naics_objects)
    else:
        profile.naics_codes.clear()

    profile.is_approved = True
    profile.save()

    return Response({
        "success": True,
        "message": "Capability profile saved successfully.",
        "created": created
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_capability_profile(request):
    profile = CapabilityProfile.objects.filter(user=request.user).first()

    if not profile:
        return Response(
            {
                'success': True,
                'editing': False,
                'processed_file_name': None,
                'profile': {
                    **{key: '' for key in PROFILE_KEYS},
                    **{key: [] for key in MATCHMAKING_PROFILE_KEYS},
                },
            },
            status=status.HTTP_200_OK,
        )

    profile_data = {
        key: getattr(profile, key, '') or ''
        for key in PROFILE_KEYS
    }

    profile_data["naics_codes"] = list(
        profile.naics_codes.values_list("code", flat=True)
    )
    for key in MATCHMAKING_PROFILE_KEYS:
        value = getattr(profile, key, [])
        profile_data[key] = value if isinstance(value, list) else []

    processed_file_name = None
    if hasattr(profile, 'source_pdf') and profile.source_pdf:
        processed_file_name = profile.source_pdf.name

    return Response(
        {
            'success': True,
            'editing': True,
            'processed_file_name': processed_file_name,
            'profile': profile_data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extract_capability_profile(request):
    uploaded_file = request.FILES.get('capability_pdf')

    if not uploaded_file:
        return Response(
            {'success': False, 'message': 'Upload a capability statement document to extract.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not is_supported_capability_document(uploaded_file):
        return Response(
            {'success': False, 'message': SUPPORTED_DOCUMENT_MESSAGE},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        extracted_text = extract_text_from_capability_document(uploaded_file)
        parsed_data = parse_capability_text(extracted_text)

        return Response(
            {
                'success': True,
                'message': 'Fields extracted successfully.',
                'processed_file_name': uploaded_file.name,
                'profile': parsed_data,
                'extracted_text': extracted_text,
            },
            status=status.HTTP_200_OK,
        )

    except pytesseract.TesseractNotFoundError:
        return Response(
            {'success': False, 'message': 'Tesseract is not installed or not in your PATH.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as exc:
        return Response(
            {'success': False, 'message': f'Failed to process document: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class OpportunityListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        contracts = Contract.objects.all().order_by('deadline', '-created_at')

        naics_code = (request.query_params.get('naics_code') or '').strip()
        agency = (request.query_params.get('agency') or '').strip()
        status_value = (request.query_params.get('status') or '').strip()
        search = (request.query_params.get('search') or '').strip()
        match_user = (request.query_params.get('match_user') or '').strip().lower() == 'true'

        if naics_code:
            contracts = contracts.filter(naics_code=naics_code)

        if agency:
            contracts = contracts.filter(agency__iexact=agency)

        if status_value:
            normalized_status = status_value.lower()

            if normalized_status == 'active':
                contracts = contracts.filter(Q(status__iexact='active') | Q(status__iexact='yes'))
            elif normalized_status == 'inactive':
                contracts = contracts.filter(Q(status__iexact='inactive') | Q(status__iexact='no'))
            else:
                contracts = contracts.filter(status__iexact=status_value)

        if search:
            contracts = contracts.filter(
                Q(title__icontains=search)
                | Q(summary__icontains=search)
                | Q(agency__icontains=search)
                | Q(partner_name__icontains=search)
                | Q(status__icontains=search)
                | Q(naics_code__icontains=search)
            )

        if match_user:
            if not request.user.is_authenticated:
                return Response(
                    {'detail': 'Authentication credentials were not provided.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            matched_contracts = get_matched_contracts_for_user(request.user, queryset=contracts)
            match_metadata = {
                item['contract'].id: {
                    'match_score': item['match_score'],
                    'match_reasons': item['match_reasons'],
                    'match_percentage': item['match_percentage'],
                    'strongest_alignment': item['strongest_alignment'],
                    'weak_alignment': item['weak_alignment'],
                    'match_breakdown': item['match_breakdown'],
                }
                for item in matched_contracts
            }
            contracts = [item['contract'] for item in matched_contracts]
        else:
            match_metadata = {}

        progress_map = {}
        contract_ids = [contract.id for contract in contracts]
        if request.user.is_authenticated:
            progress_map = {
                progress.contract_id: {
                    'contract_progress': progress.contract_progress,
                    'workflow_status': progress.workflow_status,
                    'relationship_label': progress.relationship_label,
                }
                for progress in UserContractProgress.objects.filter(
                    user=request.user,
                    contract_id__in=contract_ids,
                )
            }

        naics_codes = [contract.naics_code for contract in contracts if contract.naics_code]
        naics_category_map = {
            item['code']: item['broad_category']
            for item in NAICSCode.objects.filter(code__in=naics_codes).values('code', 'broad_category')
        }

        opportunities = []
        for contract in contracts:
            naics_code_value = contract.naics_code or ''
            naics_category = (
                contract.category
                or naics_category_map.get(naics_code_value)
                or get_category_for_naics(naics_code_value)
                or ''
            )

            opportunities.append(
                {
                    'id': contract.id,
                    'title': contract.title,
                    'description': contract.summary or '',
                    'naics_code': naics_code_value,
                    'naics_category': naics_category,
                    'agency': contract.agency or '',
                    'status': normalize_contract_status(contract.status),
                    'partner': contract.partner_name or '',
                    'source': contract.source or '',
                    'deadline': contract.deadline,
                    'hyperlink': contract.hyperlink or '',
                    'contract_progress': progress_map.get(contract.id, {}).get(
                        'contract_progress',
                        UserContractProgress.ProgressChoices.NONE,
                    ),
                    'workflow_status': progress_map.get(contract.id, {}).get(
                        'workflow_status',
                        UserContractProgress.WorkflowChoices.NOT_STARTED,
                    ),

                    'relationship_label': progress_map.get(contract.id, {}).get(
                        'relationship_label',
                        UserContractProgress.RelationshipChoices.UNASSIGNED,
                    ),

                    **match_metadata.get(contract.id, {}),
                }
            )

        serializer = OpportunitySerializer(opportunities, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
