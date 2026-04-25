from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from unittest.mock import patch

from accounts.models import CapabilityProfile, User
from core.models import Opportunity
from core.forms import CapabilityProfileForm
from core.services.capability_extraction import (
    extract_text_from_capability_document,
    parse_capability_text,
)
from core.services.matchmaking import get_matched_contracts_for_user, get_user_matchmaking_profile
from contracts.models import Contract, NAICSCode


class ProfileAccessTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login-vis/'))

    def test_notifications_requires_login(self):
        response = self.client.get(reverse('notifications'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login-vis/'))

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login-vis/'))

    def test_profile_loads_for_authenticated_user(self):
        user = User.objects.create_user(
            email='profileuser@example.com',
            password='StrongPass123!',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_exposes_signup_for_anonymous_user(self):
        response = self.client.get('/accounts/login-vis/')
        self.assertContains(response, 'Sign Up')
        self.assertNotContains(response, 'Profile')

    def test_nav_shows_profile_and_logout_for_authenticated_user(self):
        user = User.objects.create_user(
            email='navuser@example.com',
            password='StrongPass123!',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Profile')
        self.assertContains(response, 'Logout')
        self.assertNotContains(response, 'Sign Up')


class CapabilityExtractionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='extractor@example.com',
            password='StrongPass123!',
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

    def _upload(self, filename, content=b'document', content_type='application/pdf'):
        return SimpleUploadedFile(filename, content, content_type=content_type)

    def test_pdf_with_embedded_text_uses_direct_text_extraction_path(self):
        usable_text = 'Capability Statement\nAbout Us\n' + ('Cloud services ' * 20)
        pdf_file = self._upload('capability.pdf')

        with patch(
            'core.services.capability_extraction.extract_text_directly_from_pdf',
            return_value=usable_text,
        ) as mock_direct:
            with patch(
                'core.services.capability_extraction.extract_text_from_pdf_ocr',
                return_value='ocr text',
            ) as mock_ocr:
                extracted = extract_text_from_capability_document(pdf_file)

        self.assertEqual(extracted, usable_text)
        mock_direct.assert_called_once()
        mock_ocr.assert_not_called()

    def test_scanned_pdf_falls_back_to_ocr_path(self):
        pdf_file = self._upload('scanned.pdf')

        with patch(
            'core.services.capability_extraction.extract_text_directly_from_pdf',
            return_value='',
        ) as mock_direct:
            with patch(
                'core.services.capability_extraction.extract_text_from_pdf_ocr',
                return_value='OCR capability statement text',
            ) as mock_ocr:
                extracted = extract_text_from_capability_document(pdf_file)

        self.assertEqual(extracted, 'OCR capability statement text')
        mock_direct.assert_called_once()
        mock_ocr.assert_called_once()

    def test_png_jpg_and_jpeg_uploads_are_accepted_by_form_validation(self):
        for filename, content_type in [
            ('capability.png', 'image/png'),
            ('capability.jpg', 'image/jpeg'),
            ('capability.jpeg', 'image/jpeg'),
        ]:
            form = CapabilityProfileForm(
                files={'capability_pdf': self._upload(filename, b'image', content_type)}
            )
            self.assertTrue(form.is_valid(), filename)

    def test_png_upload_uses_image_extraction_path(self):
        png_file = self._upload('capability.png', b'image', 'image/png')

        with patch(
            'core.services.capability_extraction.extract_text_from_image',
            return_value='PNG OCR text',
        ) as mock_image_extract:
            extracted = extract_text_from_capability_document(png_file)

        self.assertEqual(extracted, 'PNG OCR text')
        mock_image_extract.assert_called_once()

    def test_unsupported_file_type_is_rejected(self):
        form = CapabilityProfileForm(
            files={'capability_pdf': self._upload('notes.txt', b'plain text', 'text/plain')}
        )

        self.assertFalse(form.is_valid())
        self.assertIn('Please upload a PDF, PNG, JPG, or JPEG file.', form.errors['capability_pdf'][0])

        response = self.client.post(
            '/api/profile/extract/',
            {'capability_pdf': self._upload('notes.txt', b'plain text', 'text/plain')},
            format='multipart',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['message'], 'Please upload a PDF, PNG, JPG, or JPEG file.')

    def test_section_based_parsing_maps_capability_statement_fields(self):
        text = '''
Pink Stem Solutions
Capability Statement

About Us
Pink Stem provides secure software delivery and cloud modernization for federal customers.

Core Competencies
Cloud migration
Cybersecurity compliance
Agile software development

Differentiators
Woman-owned small business with rapid delivery teams.

Past Performance
Supported GSA and VA modernization programs.

Certifications
WOSB
ISO 27001

Corporate Data
Company Name: Pink Stem Solutions
UEI: ABC123XYZ
CAGE: 7A8B9
NAICS: 541511, 541512

Point of Contact
Jane Doe
jane@pinkstem.example
(202) 555-0199
www.pinkstem.example
'''

        parsed = parse_capability_text(text)

        self.assertEqual(parsed['company_name'], 'Pink Stem Solutions')
        self.assertIn('secure software delivery', parsed['capability_summary'])
        self.assertIn('Cloud migration', parsed['core_competencies'])
        self.assertIn('Woman-owned', parsed['differentiators'])
        self.assertIn('GSA', parsed['past_performance'])
        self.assertIn('ISO 27001', parsed['certifications'])
        self.assertEqual(parsed['contact_name'], 'Jane Doe')
        self.assertEqual(parsed['contact_email'], 'jane@pinkstem.example')
        self.assertEqual(parsed['contact_phone'], '(202) 555-0199')
        self.assertEqual(parsed['website'], 'https://www.pinkstem.example')
        self.assertEqual(parsed['naics_codes'], ['541511', '541512'])

    def test_regex_fallback_extracts_contact_and_naics_from_noisy_text(self):
        text = '''
PINK STEM SOLUTIONS CAPABILITY STATEMENT
We deliver cloud modernization.
Reach us: info@pinkstem.example or 202.555.0175
Visit www.pinkstem.example
Primary NAICS 541512
'''

        parsed = parse_capability_text(text)

        self.assertEqual(parsed['contact_email'], 'info@pinkstem.example')
        self.assertEqual(parsed['contact_phone'], '202.555.0175')
        self.assertEqual(parsed['website'], 'https://www.pinkstem.example')
        self.assertEqual(parsed['naics_codes'], ['541512'])
        self.assertTrue(parsed['company_name'])

    def test_clean_primary_secondary_naics_block_extracts_all_codes(self):
        parsed = parse_capability_text(
            '''
NAICS Codes
Primary: 541511 - Custom Computer Programming Services
Secondary: 541512, 541519, 541611, 541990
'''
        )

        self.assertEqual(
            parsed['naics_codes'],
            ['541511', '541512', '541519', '541611', '541990'],
        )

    def test_noisy_primary_secondary_naics_block_repairs_common_ocr_tokens(self):
        parsed = parse_capability_text(
            '''
MAICS Codes:
Primary: S415N - Custom Computer Programming Services
Secondary: $41512, 541519, 541611, 541990
'''
        )

        self.assertEqual(
            parsed['naics_codes'],
            ['541511', '541512', '541519', '541611', '541990'],
        )

    def test_missing_sections_do_not_crash_parser(self):
        parsed = parse_capability_text('Pink Stem Solutions\ninfo@pinkstem.example')

        self.assertEqual(parsed['company_name'], 'Pink Stem Solutions')
        self.assertEqual(parsed['contact_email'], 'info@pinkstem.example')
        self.assertEqual(parsed['core_competencies'], '')

    def test_noisy_multicolumn_capability_statement_parses_expected_fields(self):
        text = '''
PF summi souatons Group, Lic Capability Statement
Mmm ovation. Quainy CAGE: 341223 Vet: §4315431231
Summit Solutions Group, LLC Is a certified small business providing innovative technology and
consulting solutions to federal, state, and local agencies. Our team specializes in agile software
development, data snstytics, and cloud architecture, with 8 strong track record of delivering secure
and scalable systems.
| pitterentiators _|
° Ful-stack software devetopment (Python, ° Proven performance with DoD and civilian
JavaScript, Java) agencies

* Cloud migration and DevOps (AWS, Azure, * 80% of staff hold active security clearances
  GcpP) * Certified In ISO 27001, CMMI Level 3, and
* Cybersecurity compilance (FISMA, AWS Partner Network
  FedRAMP} * Proprietary agile framework tailored to
* Data warehousing and business intefligence government systems
* IT project management and agile coaching ° Veteran-owned, minority-owned small
  business
  —
  Certifications
  Oefense Case Management System (DCMS)
  Client: Department of Defense Federal: VOSB, WOSB
  Contract: WQ-23432-12 Vehicles: GSA IT Schedule
  Period: Jan 2023 - Oct 2023
  POC: Maria Jennings | corporate Data _| Data
  Grants Analytics Modernization Summit Solutions Group, LLC
  cern Department of Health and Human 1234 innovation Drive Sulte 400 Arlington, VA 22202
  es
  Contract: 7500121000078 MEL 54315431231
  Period: Feb 2022 - Dec 2022 GAGE: 341223
  POC: Kevin Johnson MAICS Codes:
  Primary: S415N - Custom Computer
  | point of Contact _| of Contact Programming Services
  Secondary: $41512, 541519, 541611 , 541990
  John Smith, CEO
  [John.smith@summitsolutions.gov](mailto:John.smith@summitsolutions.gov)
  (202) 555-0134
  [www.summitsolutionsgov.com](http://www.summitsolutionsgov.com)
'''

        parsed = parse_capability_text(text)

        self.assertIn('Summit Solutions Group', parsed['company_name'])
        self.assertIn('John Smith', parsed['contact_name'])
        self.assertIn('202', parsed['contact_phone'])
        self.assertIn('555', parsed['contact_phone'])
        self.assertIn('0134', parsed['contact_phone'])
        self.assertIn('certified small business', parsed['capability_summary'])
        self.assertIn('innovative technology', parsed['capability_summary'])
        self.assertTrue(parsed['core_competencies'])
        self.assertTrue(parsed['differentiators'])
        self.assertIn('VOSB', parsed['certifications'])
        self.assertIn('WOSB', parsed['certifications'])
        self.assertIn('GSA IT Schedule', parsed['certifications'])
        self.assertIn('Defense Case Management System', parsed['past_performance'].replace('Oefense', 'Defense'))
        self.assertIn('Grants Analytics Modernization', parsed['past_performance'])
        self.assertIn('541512', parsed['naics_codes'])
        self.assertIn('541511', parsed['naics_codes'])
        self.assertIn('541519', parsed['naics_codes'])
        self.assertIn('541611', parsed['naics_codes'])
        self.assertIn('541990', parsed['naics_codes'])
        self.assertNotIn('DCMS', parsed['certifications'])
        self.assertNotEqual(parsed['contact_phone'], '54315431231')

    def test_profile_extraction_endpoint_still_works_end_to_end(self):
        extracted_text = '''
Pink Stem Solutions
About Us
Secure cloud delivery for federal agencies.
Core Competencies
Cloud migration
NAICS 541512
Contact Information
Jane Doe
jane@pinkstem.example
202-555-0188
'''

        with patch('core.views.extract_text_from_capability_document', return_value=extracted_text):
            response = self.client.post(
                '/api/profile/extract/',
                {'capability_pdf': self._upload('capability.pdf')},
                format='multipart',
                **self.auth_headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['processed_file_name'], 'capability.pdf')
        self.assertIn('profile', response.data)
        self.assertEqual(response.data['profile']['contact_email'], 'jane@pinkstem.example')
        self.assertEqual(response.data['profile']['naics_codes'], ['541512'])

    def test_profile_extraction_endpoint_returns_noisy_naics_codes(self):
        extracted_text = '''
MAICS Codes:
Primary: S415N - Custom Computer Programming Services
Secondary: $41512, 541519, 541611, 541990
'''

        with patch('core.views.extract_text_from_capability_document', return_value=extracted_text):
            response = self.client.post(
                '/api/profile/extract/',
                {'capability_pdf': self._upload('capability.pdf')},
                format='multipart',
                **self.auth_headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['profile']['naics_codes'],
            ['541511', '541512', '541519', '541611', '541990'],
        )

    def test_save_capability_profile_creates_missing_naics_reference_rows(self):
        self.assertFalse(NAICSCode.objects.filter(code='541990').exists())

        response = self.client.post(
            '/api/profile/save/',
            {
                'company_name': 'Summit Solutions Group',
                'naics_codes': ['541511', '541512', '541519', '541611', '541990'],
            },
            format='json',
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        profile = CapabilityProfile.objects.get(user=self.user)
        self.assertEqual(
            set(profile.naics_codes.values_list('code', flat=True)),
            {'541511', '541512', '541519', '541611', '541990'},
        )
        self.assertTrue(NAICSCode.objects.filter(code='541990').exists())


class OpportunityApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='matcher@example.com',
            password='StrongPass123!',
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_headers = {'HTTP_AUTHORIZATION': f'Token {self.token.key}'}

        Contract.objects.create(
            source='procurement',
            title='Cybersecurity Support Services',
            summary='Cyber operations and compliance support.',
            naics_code='541330',
            agency='DoD',
            status='Reviewing',
            partner_name='Northwind Systems',
            category='engineering',
        )
        Contract.objects.create(
            source='procurement',
            title='Facilities Maintenance',
            summary='General building maintenance support.',
            naics_code='561210',
            agency='GSA',
            status='Submitted',
            partner_name='Atlas Facilities',
        )
        Contract.objects.create(
            source='procurement',
            title='Cloud Engineering Contract',
            summary='Secure cloud migration for federal systems.',
            naics_code='541330',
            agency='VA',
            status='Drafting',
            partner_name='Skyline Tech',
        )

    def test_list_all_opportunities(self):
        response = self.client.get('/api/opportunities/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertNotIn('match_score', response.data[0])
        self.assertNotIn('match_reasons', response.data[0])

    def test_filter_by_naics_code(self):
        response = self.client.get('/api/opportunities/?naics_code=541330')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(all(item['naics_code'] == '541330' for item in response.data))

    def test_dashboard_fields_are_present_in_opportunity_payload(self):
        response = self.client.get('/api/opportunities/?naics_code=541330')

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertIn('title', response.data[0])
        self.assertIn('description', response.data[0])
        self.assertIn('naics_code', response.data[0])
        self.assertIn('naics_category', response.data[0])
        self.assertIn('agency', response.data[0])
        self.assertIn('status', response.data[0])
        self.assertIn('partner', response.data[0])
        self.assertIn('contract_progress', response.data[0])
        self.assertIn('workflow_status', response.data[0])

    def test_opportunity_payload_includes_naics_category(self):
        response = self.client.get('/api/opportunities/?search=cyber')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['naics_category'], 'engineering')

    def test_search_by_keyword(self):
        response = self.client.get('/api/opportunities/?search=cloud')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Cloud Engineering Contract')

    def test_apply_naics_and_search_together(self):
        response = self.client.get('/api/opportunities/?naics_code=541330&search=cyber')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Cybersecurity Support Services')

    def test_filter_by_agency_case_insensitive(self):
        response = self.client.get('/api/opportunities/?agency=dod')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['agency'], 'DoD')

    def test_filter_by_status_case_insensitive(self):
        response = self.client.get('/api/opportunities/?status=submitted')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'Submitted')

    def test_status_values_are_normalized_in_payload_and_filtering(self):
        Contract.objects.create(
            source='procurement',
            title='Legacy Active Contract',
            summary='Legacy active row.',
            naics_code='541511',
            agency='NASA',
            status='Yes',
        )
        Contract.objects.create(
            source='procurement',
            title='Legacy Inactive Contract',
            summary='Legacy inactive row.',
            naics_code='541512',
            agency='DOE',
            status='No',
        )

        response = self.client.get('/api/opportunities/?agency=nasa')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['status'], 'Active')

        active_filter_response = self.client.get('/api/opportunities/?status=active')
        self.assertEqual(active_filter_response.status_code, 200)
        self.assertTrue(
            any(item['title'] == 'Legacy Active Contract' for item in active_filter_response.data)
        )
        self.assertTrue(
            all(item['status'] == 'Active' for item in active_filter_response.data)
        )

        inactive_filter_response = self.client.get('/api/opportunities/?status=inactive')
        self.assertEqual(inactive_filter_response.status_code, 200)
        self.assertTrue(
            any(item['title'] == 'Legacy Inactive Contract' for item in inactive_filter_response.data)
        )
        self.assertTrue(
            all(item['status'] == 'Inactive' for item in inactive_filter_response.data)
        )

    def test_apply_all_filters_together(self):
        response = self.client.get('/api/opportunities/?search=cloud&naics_code=541330&agency=va&status=drafting')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Cloud Engineering Contract')

    def test_search_matches_partner_name(self):
        response = self.client.get('/api/opportunities/?search=northwind')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['partner'], 'Northwind Systems')

    def test_match_user_filters_by_capability_profile_naics_codes(self):
        naics_code = NAICSCode.objects.create(code='541330', title='Engineering Services')
        profile = CapabilityProfile.objects.create(
            user=self.user,
            company_name='Match Co',
        )
        profile.naics_codes.set([naics_code])

        response = self.client.get('/api/opportunities/?match_user=true', **self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(all(item['naics_code'] == '541330' for item in response.data))
        self.assertTrue(all(item['match_score'] > 0 for item in response.data))
        self.assertTrue(all(item['match_reasons'] for item in response.data))

    def test_match_user_requires_authentication(self):
        response = self.client.get('/api/opportunities/?match_user=true')

        self.assertEqual(response.status_code, 401)

    def test_get_user_matchmaking_profile_returns_normalized_profile_data(self):
        naics_code = NAICSCode.objects.create(code='541512', title='Computer Systems Design Services')
        profile = CapabilityProfile.objects.create(
            user=self.user,
            company_name='Cloud Match Co',
            capability_summary='Secure cloud engineering and migration.',
            core_competencies='Cloud migration, cybersecurity, compliance',
            differentiators='Rapid delivery for federal agencies',
            certifications='ISO 27001',
            past_performance='Delivered cloud migration support for VA.',
        )
        profile.naics_codes.set([naics_code])

        normalized = get_user_matchmaking_profile(self.user)

        self.assertTrue(normalized['has_profile'])
        self.assertTrue(normalized['has_matchable_data'])
        self.assertEqual(normalized['company_name'], 'Cloud Match Co')
        self.assertEqual(normalized['naics_codes'], ['541512'])
        self.assertIn('cloud', normalized['keywords'])
        self.assertIn('iso', normalized['certification_keywords'])

    def test_get_user_matchmaking_profile_handles_missing_and_incomplete_profile(self):
        missing = get_user_matchmaking_profile(self.user)
        self.assertFalse(missing['has_profile'])
        self.assertFalse(missing['has_matchable_data'])
        self.assertEqual(missing['naics_codes'], [])

        CapabilityProfile.objects.create(user=self.user, company_name='')
        incomplete = get_user_matchmaking_profile(self.user)
        self.assertTrue(incomplete['has_profile'])
        self.assertFalse(incomplete['has_matchable_data'])

    def test_match_user_ranks_keyword_overlap_above_plain_naics_match(self):
        naics_code = NAICSCode.objects.create(code='541330', title='Engineering Services')
        profile = CapabilityProfile.objects.create(
            user=self.user,
            company_name='Cloud Co',
            core_competencies='cloud migration',
        )
        profile.naics_codes.set([naics_code])

        response = self.client.get('/api/opportunities/?match_user=true', **self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['title'], 'Cloud Engineering Contract')
        self.assertGreater(response.data[0]['match_score'], response.data[1]['match_score'])
        self.assertIn('Keyword overlap with profile capabilities', response.data[0]['match_reasons'])

    def test_text_only_profile_can_return_text_based_matches(self):
        CapabilityProfile.objects.create(
            user=self.user,
            company_name='Facilities Co',
            core_competencies='facilities maintenance building upkeep',
        )

        response = self.client.get('/api/opportunities/?match_user=true', **self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Facilities Maintenance')
        self.assertGreater(response.data[0]['match_score'], 0)

    def test_match_user_returns_empty_list_when_nothing_matches(self):
        CapabilityProfile.objects.create(
            user=self.user,
            company_name='Marine Biology Co',
            core_competencies='marine biology coral reef surveys',
        )

        response = self.client.get('/api/opportunities/?match_user=true', **self.auth_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_get_matched_contracts_for_user_respects_passed_queryset(self):
        naics_code = NAICSCode.objects.create(code='541330', title='Engineering Services')
        profile = CapabilityProfile.objects.create(user=self.user)
        profile.naics_codes.set([naics_code])

        queryset = Contract.objects.filter(agency='VA')
        matches = get_matched_contracts_for_user(self.user, queryset=queryset)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['contract'].title, 'Cloud Engineering Contract')
        self.assertGreater(matches[0]['match_score'], 0)

    def test_opportunity_api_ignores_legacy_core_opportunity_rows(self):
        Opportunity.objects.create(
            title='Legacy Opportunity Row',
            description='This should not appear in the active API.',
            naics_code='999999',
            agency='Legacy Agency',
            status='Legacy',
        )

        response = self.client.get('/api/opportunities/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertFalse(any(item['title'] == 'Legacy Opportunity Row' for item in response.data))
