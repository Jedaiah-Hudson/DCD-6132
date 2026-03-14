from django import forms


class CapabilityProfileForm(forms.Form):
    capability_pdf = forms.FileField(
        label='Upload Capability Statement (PDF)',
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
        if uploaded_file and not uploaded_file.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Please upload a PDF file.')
        return uploaded_file
