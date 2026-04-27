import re

from accounts.models import CapabilityProfile
from contracts.management.services.naics_utils import get_category_for_naics
from contracts.models import Contract


KEYWORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+#&.-]{2,}\b")
STOP_WORDS = {
    "and",
    "are",
    "for",
    "from",
    "our",
    "the",
    "this",
    "that",
    "with",
    "your",
    "services",
    "support",
    "company",
    "capability",
    "capabilities",
}


def _normalize_text(value):
    return " ".join(str(value or "").split())


def _keywords(value):
    words = {
        word.lower().strip(".")
        for word in KEYWORD_RE.findall(value or "")
    }
    return {word for word in words if word not in STOP_WORDS and len(word) > 2}


def get_user_matchmaking_profile(user):
    profile = CapabilityProfile.objects.filter(user=user).prefetch_related("naics_codes").first()

    empty_profile = {
        "profile": None,
        "has_profile": False,
        "company_name": "",
        "naics_codes": [],
        "naics_categories": [],
        "capability_summary": "",
        "core_competencies": "",
        "differentiators": "",
        "certifications": "",
        "past_performance": "",
        "keywords": set(),
        "certification_keywords": set(),
        "has_matchable_data": False,
    }

    if not profile:
        return empty_profile

    naics_codes = list(profile.naics_codes.values_list("code", flat=True))
    text_fields = {
        "company_name": _normalize_text(profile.company_name),
        "capability_summary": _normalize_text(profile.capability_summary),
        "core_competencies": _normalize_text(profile.core_competencies),
        "differentiators": _normalize_text(profile.differentiators),
        "certifications": _normalize_text(profile.certifications),
        "past_performance": _normalize_text(profile.past_performance),
    }
    profile_text = " ".join(text_fields.values())
    certification_keywords = _keywords(text_fields["certifications"])
    keywords = _keywords(profile_text)
    naics_categories = sorted(
        {
            category
            for category in (get_category_for_naics(code) for code in naics_codes)
            if category
        }
    )

    return {
        "profile": profile,
        "has_profile": True,
        "naics_codes": naics_codes,
        "naics_categories": naics_categories,
        "keywords": keywords,
        "certification_keywords": certification_keywords,
        "has_matchable_data": bool(naics_codes or keywords),
        **text_fields,
    }


def _score_contract(contract, matchmaking_profile):
    score = 0
    reasons = []
    contract_naics = (contract.naics_code or "").strip()
    user_naics_codes = set(matchmaking_profile["naics_codes"])

    if contract_naics and contract_naics in user_naics_codes:
        score += 100
        reasons.append(f"Matched NAICS code {contract_naics}")
    else:
        contract_category = contract.category or get_category_for_naics(contract_naics)
        if contract_category and contract_category in matchmaking_profile["naics_categories"]:
            score += 45
            reasons.append(f"Matched NAICS category {contract_category.replace('_', ' ')}")

    contract_text = " ".join(
        [
            contract.title or "",
            contract.summary or "",
            contract.agency or "",
            contract.sub_agency or "",
            contract.partner_name or "",
        ]
    )
    contract_keywords = _keywords(contract_text)
    keyword_overlap = sorted(matchmaking_profile["keywords"] & contract_keywords)
    certification_overlap = sorted(matchmaking_profile["certification_keywords"] & contract_keywords)

    if keyword_overlap:
        overlap_score = min(len(keyword_overlap), 6) * 6
        score += overlap_score
        reasons.append("Keyword overlap with profile capabilities")

    if certification_overlap:
        score += min(len(certification_overlap), 4) * 8
        reasons.append("Certification keyword overlap")

    return {
        "contract": contract,
        "match_score": score,
        "match_reasons": reasons,
        "keyword_overlap": keyword_overlap,
        "certification_overlap": certification_overlap,
    }


def get_matched_contracts_for_user(user, queryset=None):
    matchmaking_profile = get_user_matchmaking_profile(user)
    if not matchmaking_profile["has_matchable_data"]:
        return []

    contracts = queryset if queryset is not None else Contract.objects.all().order_by("deadline", "-created_at")
    scored_matches = []

    for contract in contracts:
        scored = _score_contract(contract, matchmaking_profile)
        if scored["match_score"] > 0:
            scored_matches.append(scored)

    scored_matches.sort(
        key=lambda item: (
            -item["match_score"],
            item["contract"].deadline is None,
            item["contract"].deadline,
            -item["contract"].created_at.timestamp() if item["contract"].created_at else 0,
        )
    )
    return scored_matches
