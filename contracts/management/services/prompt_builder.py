def build_capability_profile_text(profile):
    naics = ", ".join([str(n.code) for n in profile.naics_codes.all()])

    return f"""
Company Name: {profile.company_name}

Capability Summary:
{profile.capability_summary}

Core Competencies:
{profile.core_competencies}

Differentiators:
{profile.differentiators}

Certifications:
{profile.certifications}

Past Performance:
{profile.past_performance}

NAICS Codes:
{naics}

Contact:
{profile.contact_name} | {profile.contact_email} | {profile.contact_phone}

Website:
{profile.website}
"""