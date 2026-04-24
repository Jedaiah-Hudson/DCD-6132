from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import json
import re
import pytesseract
import pypdfium2 as pdfium
from django.db.models import Q

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from accounts.models import CapabilityProfile, User
from contracts.models import Contract, NAICSCode, UserContractProgress
from contracts.management.services.naics_utils import get_category_for_naics
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


def extract_text_from_pdf(uploaded_file):
    uploaded_file.seek(0)
    pdf_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    pdf = pdfium.PdfDocument(pdf_bytes)
    page_texts = []

    for index in range(len(pdf)):
        page = pdf[index]
        page_image = page.render(scale=2).to_pil()
        text = pytesseract.image_to_string(page_image).strip()
        if text:
            page_texts.append(text)
        page.close()

    pdf.close()
    return '\n\n'.join(page_texts).strip()


def parse_capability_text(text):
    parsed = {key: '' for key in PROFILE_KEYS}
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    section_headers = [
        ('company_name', ['company name']),
        ('capability_summary', ['capability summary', 'capabilities statement', 'summary', 'about us']),
        ('core_competencies', ['core competencies', 'competencies']),
        ('differentiators', ['differentiators']),
        ('naics_codes', ['naics codes', 'naics']),
        ('certifications', ['licenses & certifications', 'licenses and certifications', 'certifications']),
        ('past_performance', ['past performance']),
        ('contact_name', ['contact name']),
        ('contact_email', ['contact email', 'email']),
        ('contact_phone', ['contact phone', 'phone']),
        ('website', ['website']),
    ]

    def normalize_line(line):
        return re.sub(r'[^a-z0-9\s:&/-]', '', line.lower()).strip()

    def find_section(line):
        cleaned = normalize_line(line)
        for key, headers in section_headers:
            for header in headers:
                if cleaned == header or cleaned.startswith(header + ':'):
                    return key
        return None

    current_section = None
    section_content = {key: [] for key in PROFILE_KEYS}

    for line in lines:
        section_key = find_section(line)
        if section_key:
            current_section = section_key
            if ':' in line:
                value = line.split(':', 1)[1].strip()
                if value:
                    section_content[section_key].append(value)
            continue

        if current_section:
            section_content[current_section].append(line)

    for key, content_lines in section_content.items():
        if content_lines:
            parsed[key] = '\n'.join(content_lines).strip()

    full_text = '\n'.join(lines)

    if not parsed['contact_email']:
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', full_text)
        if email_match:
            parsed['contact_email'] = email_match.group(0)

    if not parsed['contact_phone']:
        phone_match = re.search(r'(\+?1[\s\.-]?)?\(?\d{3}\)?[\s\.-]?\d{3}[\s\.-]?\d{4}', full_text)
        if phone_match:
            parsed['contact_phone'] = phone_match.group(0)

    if not parsed['website']:
        website_match = re.search(r'(https?://\S+|www\.\S+)', full_text)
        if website_match:
            parsed['website'] = website_match.group(0)

    if not parsed['naics_codes']:
        naics_matches = re.findall(r'\b\d{6}\b', full_text)
        if naics_matches:
            parsed['naics_codes'] = sorted(set(naics_matches))

    if not parsed['certifications']:
        cert_lines = []
        for line in lines:
            if re.search(r'\b(iso|cmmi|sam|8a|hubzone|wosb|sdvosb)\b', line, re.IGNORECASE):
                cert_lines.append(line)
        if cert_lines:
            parsed['certifications'] = '\n'.join(cert_lines)

    def normalize_website(value):
        website = value.strip().rstrip('.,;)')
        website = website.replace('https:/www.', 'https://www.')
        website = website.replace('http:/www.', 'http://www.')
        website = re.sub(r'^https:/([^/])', r'https://\1', website)
        website = re.sub(r'^http:/([^/])', r'http://\1', website)
        if website.startswith('www.'):
            website = 'https://' + website
        return website

    if parsed['website']:
        parsed['website'] = normalize_website(parsed['website'])

    if not parsed['company_name'] and lines:
        parsed['company_name'] = lines[0]

    if not parsed['capability_summary'] and len(lines) > 1:
        parsed['capability_summary'] = lines[1]

    return parsed

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

            # start fresh for every uploaded PDF
            structured_data = {key: '' for key in PROFILE_KEYS}
            submitted_data = None

            if not uploaded_file:
                profile_form = CapabilityProfileForm(request.POST, request.FILES)
                profile_form.add_error('capability_pdf', 'Upload a PDF to run OCR.')
            elif not uploaded_file.name.lower().endswith('.pdf'):
                profile_form = CapabilityProfileForm(request.POST, request.FILES)
                profile_form.add_error('capability_pdf', 'Please upload a PDF file.')
            else:
                try:
                    processed_file_name = uploaded_file.name
                    extracted_text = extract_text_from_pdf(uploaded_file)
                    parsed_data = parse_capability_text(extracted_text)

                    structured_data.update(parsed_data)
                    profile_form = CapabilityProfileForm(initial=structured_data)

                except pytesseract.TesseractNotFoundError:
                    ocr_error = 'Tesseract is not installed or not in your PATH.'
                    profile_form = CapabilityProfileForm()
                except Exception as exc:
                    ocr_error = f'Failed to process PDF: {exc}'
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
                            extracted_text = extract_text_from_pdf(uploaded_file)
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

    # remove many-to-many field first
    naics_codes = capability_data.pop("naics_codes", [])

    profile, created = CapabilityProfile.objects.update_or_create(
        user=request.user,
        defaults=capability_data
    )

    # save dropdown selections
    if naics_codes:
        naics_objects = NAICSCode.objects.filter(code__in=naics_codes)
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
                'profile': {key: '' for key in PROFILE_KEYS},
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
            {'success': False, 'message': 'Upload a PDF to run OCR.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not uploaded_file.name.lower().endswith('.pdf'):
        return Response(
            {'success': False, 'message': 'Please upload a PDF file.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        extracted_text = extract_text_from_pdf(uploaded_file)
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
            {'success': False, 'message': f'Failed to process PDF: {exc}'},
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

            profile = CapabilityProfile.objects.filter(user=request.user).first()
            if not profile or not profile.naics_codes.exists():
                return Response([], status=status.HTTP_200_OK)

            user_naics_codes = list(profile.naics_codes.values_list('code', flat=True))
            contracts = contracts.filter(naics_code__in=user_naics_codes)

        progress_map = {}
        if request.user.is_authenticated:
            progress_map = {
                progress.contract_id: {
                    'contract_progress': progress.contract_progress,
                    'workflow_status': progress.workflow_status,
                }
                for progress in UserContractProgress.objects.filter(
                    user=request.user,
                    contract_id__in=contracts.values_list('id', flat=True),
                )
            }

        naics_codes = [code for code in contracts.values_list('naics_code', flat=True) if code]
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
                    'status': contract.status or '',
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
                }
            )

        serializer = OpportunitySerializer(opportunities, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
