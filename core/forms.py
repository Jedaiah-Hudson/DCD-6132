from django import forms

from core.services.capability_extraction import is_supported_capability_document


class CapabilityProfileForm(forms.Form):
    capability_pdf = forms.FileField(
        label='Upload Capability Statement (PDF, PNG, JPG, or JPEG)',
        required=False,
    )
    company_name = forms.CharField(required=False)
    capability_summary = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
    core_competencies = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
    differentiators = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
    naics_codes = forms.CharField(required=False)
    certifications = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
    past_performance = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
    contact_name = forms.CharField(required=False)
    contact_email = forms.EmailField(required=False)
    contact_phone = forms.CharField(required=False)
    website = forms.URLField(required=False)

    def clean_capability_pdf(self):
        uploaded_file = self.cleaned_data.get('capability_pdf')
        if uploaded_file and not is_supported_capability_document(uploaded_file):
            raise forms.ValidationError('Please upload a PDF, PNG, JPG, or JPEG file.')
        return uploaded_file
