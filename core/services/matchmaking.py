import hashlib
import logging
import math
import os
import re

from accounts.models import CapabilityProfile
from accounts.profile_options import MATCHMAKING_OPTION_FIELDS
from contracts.management.services.naics_utils import get_category_for_naics
from contracts.models import Contract

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


logger = logging.getLogger(__name__)

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
    "federal",
    "contract",
    "contracts",
    "service",
}
EMBEDDING_MODEL_ENV = "OPENAI_EMBEDDING_MODEL"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_MAX_POINTS = 35
NAICS_MAX_POINTS = 25
CAPABILITY_MAX_POINTS = 20
CERTIFICATION_MAX_POINTS = 10
TIMELINE_MAX_POINTS = 10
SEMANTIC_SIMILARITY_FLOOR = 0.72
_EMBEDDING_CACHE = {}

OPTION_MATCH_TERMS = {
    "Software Development": ["software", "application", "development", "web", "portal", "programming"],
    "Cybersecurity": ["cyber", "cybersecurity", "security", "compliance", "monitoring", "incident"],
    "Data Analytics": ["data", "analytics", "dashboard", "reporting", "analysis", "metrics"],
    "AI / Machine Learning": ["ai", "artificial intelligence", "machine learning", "predictive", "modeling"],
    "Cloud Services": ["cloud", "migration", "hosted", "aws", "azure", "infrastructure"],
    "IT Support": ["it support", "help desk", "technical support", "systems", "network"],
    "Workforce Training": ["training", "workforce", "learning", "curriculum", "instruction"],
    "Manufacturing Support": ["manufacturing", "production", "industrial", "supply", "assembly"],
    "Grant Writing": ["grant", "proposal", "writing", "application"],
    "Project Management": ["project management", "program management", "coordination", "pmo"],
    "Business Consulting": ["consulting", "advisory", "strategy", "business", "management"],
    "Engineering Services": ["engineering", "architecture", "design", "technical services"],
    "Robotics / Automation": ["robotics", "automation", "automated", "process automation"],
    "Government": ["government", "federal", "agency", "public sector", "gsa", "dod", "va", "nasa"],
    "Manufacturing": ["manufacturing", "industrial", "production", "factory"],
    "Education": ["education", "school", "student", "curriculum", "training", "stem"],
    "Healthcare": ["health", "healthcare", "medical", "hospital", "hhs", "va"],
    "Defense": ["defense", "dod", "army", "navy", "air force", "military"],
    "Transportation": ["transportation", "logistics", "fleet", "vehicle", "transit"],
    "Energy": ["energy", "utility", "power", "electric", "doe"],
    "Construction": ["construction", "building", "facility", "renovation"],
    "Nonprofit": ["nonprofit", "community", "foundation"],
    "Workforce Development": ["workforce", "employment", "career", "training"],
    "Technology": ["technology", "software", "it", "cloud", "data", "digital"],
    "Public Safety": ["public safety", "emergency", "law enforcement", "security"],
    "Prime Contract": ["prime", "prime contract"],
    "Subcontract": ["subcontract", "subcontractor", "teaming"],
    "Partnership": ["partnership", "partner", "collaboration", "teaming"],
    "Grant": ["grant", "funding", "award"],
    "Training Contract": ["training", "instruction", "course", "curriculum"],
    "Technical Services": ["technical services", "technical support", "engineering", "it services"],
    "Consulting Contract": ["consulting", "advisory", "strategy"],
    "Research Opportunity": ["research", "study", "analysis", "development"],
    "Application Development": ["application", "software", "development", "portal", "web"],
    "Data Dashboards": ["dashboard", "reporting", "data visualization", "analytics"],
    "Automation": ["automation", "automated", "workflow", "process"],
    "Cloud Migration": ["cloud migration", "migration", "cloud"],
    "AI": ["ai", "artificial intelligence"],
    "Machine Learning": ["machine learning", "predictive", "model"],
    "Curriculum Development": ["curriculum", "course", "training", "instruction"],
    "STEM Education": ["stem", "education", "student", "science", "technology"],
    "Digital Transformation": ["digital transformation", "modernization", "digital"],
    "Compliance": ["compliance", "regulatory", "nist", "iso"],
    "Database Management": ["database", "data management", "sql", "records"],
    "Technical Writing": ["technical writing", "documentation", "proposal", "manual"],
    "Procurement Support": ["procurement", "acquisition", "contracting"],
    "Georgia": ["georgia", "atlanta", "ga"],
    "Southeast": ["southeast", "southeastern", "georgia", "atlanta", "florida", "alabama", "carolina"],
    "Nationwide": ["nationwide", "national", "remote", "multiple locations"],
    "Remote": ["remote", "virtual", "telework"],
    "Local Only": ["local", "onsite", "on-site"],
    "Hybrid / On-site": ["hybrid", "on-site", "onsite"],
}


def _normalize_text(value):
    return " ".join(str(value or "").split())


def _keywords(value):
    words = {
        word.lower().strip(".")
        for word in KEYWORD_RE.findall(value or "")
    }
    return {word for word in words if word not in STOP_WORDS and len(word) > 2}


def _clamp(value, lower=0, upper=100):
    return max(lower, min(upper, value))


def _humanize_keyword(keyword):
    label = str(keyword or "").replace("_", " ").replace("-", " ").strip()
    if not label:
        return ""

    acronym_labels = {
        "api": "API",
        "apis": "APIs",
        "ai": "AI",
        "ml": "ML",
        "iso": "ISO",
        "fedramp": "FedRAMP",
        "nist": "NIST",
        "cmmc": "CMMC",
        "sba": "SBA",
    }
    lower_label = label.lower()
    if lower_label in acronym_labels:
        return acronym_labels[lower_label]

    return " ".join(part.capitalize() for part in label.split())


def _append_unique(items, value, limit=None):
    if value and value not in items and (limit is None or len(items) < limit):
        items.append(value)


def _build_profile_text(profile, naics_codes):
    structured_sections = []
    for field_name in MATCHMAKING_OPTION_FIELDS:
        values = getattr(profile, field_name, []) or []
        if values:
            structured_sections.append(f"{field_name.replace('_', ' ').title()}: {', '.join(values)}")

    return _normalize_text(
        " ".join(
            [
                profile.company_name or "",
                profile.capability_summary or "",
                profile.core_competencies or "",
                profile.differentiators or "",
                profile.certifications or "",
                profile.past_performance or "",
                " ".join(naics_codes),
                " ".join(structured_sections),
                profile.ocr_extracted_text or "",
            ]
        )
    )


def _build_contract_text(contract):
    return _normalize_text(
        " ".join(
            [
                contract.title or "",
                contract.summary or "",
                contract.agency or "",
                contract.sub_agency or "",
                contract.naics_code or "",
                contract.partner_name or "",
                contract.category or "",
                contract.status or "",
                contract.source or "",
                contract.procurement_portal or "",
            ]
        )
    )


def _get_embedding_model():
    return os.environ.get(EMBEDDING_MODEL_ENV) or DEFAULT_EMBEDDING_MODEL


def _embedding_cache_key(model, text):
    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return f"{model}:{digest}"


def _get_embedding(text):
    normalized_text = _normalize_text(text)
    if not normalized_text or not os.environ.get("OPENAI_API_KEY"):
        return None

    model = _get_embedding_model()
    cache_key = _embedding_cache_key(model, normalized_text)
    if cache_key in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[cache_key]

    if OpenAI is None:
        logger.warning("OpenAI package unavailable; using rule-based matchmaking only")
        return None

    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.embeddings.create(
            model=model,
            input=normalized_text[:12000],
        )
        embedding = list(response.data[0].embedding)
        _EMBEDDING_CACHE[cache_key] = embedding
        return embedding
    except Exception as exc:
        logger.warning("OpenAI embedding unavailable; using rule-based matchmaking only: %s", exc.__class__.__name__)
        return None


def _cosine_similarity(left, right):
    if not left or not right or len(left) != len(right):
        return None

    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return None

    return dot_product / (left_norm * right_norm)


def _embedding_points(similarity):
    if similarity is None or similarity < SEMANTIC_SIMILARITY_FLOOR:
        return 0

    scaled = (similarity - SEMANTIC_SIMILARITY_FLOOR) / (1 - SEMANTIC_SIMILARITY_FLOOR)
    return _clamp(round(scaled * EMBEDDING_MAX_POINTS), 0, EMBEDDING_MAX_POINTS)


def _normalize_option_values(values, allowed_options):
    if not isinstance(values, list):
        return []

    allowed_lookup = {option.lower(): option for option in allowed_options}
    normalized = []
    for value in values:
        allowed_value = allowed_lookup.get(str(value or "").strip().lower())
        if allowed_value and allowed_value not in normalized:
            normalized.append(allowed_value)
    return normalized


def _option_matches(option, contract_text):
    normalized_contract_text = contract_text.lower()
    terms = OPTION_MATCH_TERMS.get(option, [option])
    return any(term.lower() in normalized_contract_text for term in terms)


def _matching_options(options, contract_text):
    return [option for option in options if _option_matches(option, contract_text)]


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
        "profile_text": "",
        "services_offered": [],
        "target_industries": [],
        "preferred_opportunity_types": [],
        "matchmaking_tags": [],
        "geographic_preferences": [],
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
    embedding_text = _build_profile_text(profile, naics_codes)
    certification_keywords = _keywords(text_fields["certifications"])
    keywords = _keywords(profile_text)
    structured_fields = {
        field_name: _normalize_option_values(
            getattr(profile, field_name, []),
            allowed_options,
        )
        for field_name, allowed_options in MATCHMAKING_OPTION_FIELDS.items()
    }
    structured_text = " ".join(
        value
        for values in structured_fields.values()
        for value in values
    )
    keywords.update(_keywords(structured_text))
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
        "profile_text": embedding_text,
        "has_matchable_data": bool(naics_codes or keywords or structured_text),
        **structured_fields,
        **text_fields,
    }


def _score_contract(contract, matchmaking_profile, profile_embedding=None):
    reasons = []
    strongest_alignment = []
    weak_alignment = []
    match_breakdown = {
        "embedding": 0,
        "naics": 0,
        "capabilities": 0,
        "certifications": 0,
        "timeline": 0,
    }
    contract_naics = (contract.naics_code or "").strip()
    user_naics_codes = set(matchmaking_profile["naics_codes"])

    if contract_naics and contract_naics in user_naics_codes:
        match_breakdown["naics"] = NAICS_MAX_POINTS
        reasons.append(f"Matched NAICS code {contract_naics}")
        _append_unique(strongest_alignment, f"NAICS {contract_naics}")
    else:
        contract_category = contract.category or get_category_for_naics(contract_naics)
        if contract_category and contract_category in matchmaking_profile["naics_categories"]:
            match_breakdown["naics"] = round(NAICS_MAX_POINTS * 0.55)
            category_label = contract_category.replace("_", " ")
            reasons.append(f"Matched NAICS category {category_label}")
            family = f"{contract_naics[:3]}xxx" if len(contract_naics) >= 3 else "related"
            _append_unique(strongest_alignment, f"NAICS {family} category")
        elif user_naics_codes or contract_naics:
            weak_alignment.append("No matching NAICS code found")

    contract_text = _build_contract_text(contract)
    contract_keywords = _keywords(contract_text)
    keyword_overlap = sorted(matchmaking_profile["keywords"] & contract_keywords)
    certification_overlap = sorted(matchmaking_profile["certification_keywords"] & contract_keywords)
    service_matches = _matching_options(matchmaking_profile["services_offered"], contract_text)
    industry_matches = _matching_options(matchmaking_profile["target_industries"], contract_text)
    opportunity_type_matches = _matching_options(matchmaking_profile["preferred_opportunity_types"], contract_text)
    tag_matches = _matching_options(matchmaking_profile["matchmaking_tags"], contract_text)
    geographic_matches = _matching_options(matchmaking_profile["geographic_preferences"], contract_text)

    if keyword_overlap:
        match_breakdown["capabilities"] += _clamp(
            round((min(len(keyword_overlap), 6) / 6) * CAPABILITY_MAX_POINTS),
            0,
            10,
        )
        reasons.append("Keyword overlap with profile capabilities")
        for keyword in keyword_overlap[:3]:
            _append_unique(strongest_alignment, _humanize_keyword(keyword), limit=4)

    structured_capability_points = (
        min(len(service_matches), 2) * 3
        + min(len(tag_matches), 2) * 2
        + min(len(industry_matches), 1) * 2
        + min(len(opportunity_type_matches), 1) * 1
        + min(len(geographic_matches), 1) * 1
    )
    if structured_capability_points:
        match_breakdown["capabilities"] = _clamp(
            match_breakdown["capabilities"] + structured_capability_points,
            0,
            CAPABILITY_MAX_POINTS,
        )

    for option in service_matches[:2]:
        reasons.append(f"Matched selected service {option}")
        _append_unique(strongest_alignment, f"Service match: {option}", limit=10)
    for option in industry_matches[:1]:
        reasons.append(f"Matched target industry {option}")
        _append_unique(strongest_alignment, f"Industry match: {option}", limit=10)
    for option in opportunity_type_matches[:1]:
        reasons.append(f"Matched opportunity type {option}")
        _append_unique(strongest_alignment, f"Opportunity type match: {option}", limit=10)
    for option in tag_matches[:2]:
        reasons.append(f"Matched matchmaking tag {option}")
        _append_unique(strongest_alignment, f"Tag match: {option}", limit=10)
    for option in geographic_matches[:1]:
        reasons.append(f"Matched geographic preference {option}")
        _append_unique(strongest_alignment, f"Geographic match: {option}", limit=10)

    if not keyword_overlap and not service_matches and not tag_matches and matchmaking_profile["keywords"]:
        weak_alignment.append("Limited capability keyword overlap")
    if matchmaking_profile["services_offered"] and not service_matches:
        weak_alignment.append("No selected services matched this opportunity")
    if matchmaking_profile["target_industries"] and not industry_matches:
        weak_alignment.append("No target industry match found")
    if matchmaking_profile["geographic_preferences"] and not geographic_matches:
        weak_alignment.append("No geographic preference match found")

    if certification_overlap:
        match_breakdown["certifications"] = _clamp(
            round((min(len(certification_overlap), 4) / 4) * CERTIFICATION_MAX_POINTS),
            0,
            CERTIFICATION_MAX_POINTS,
        )
        reasons.append("Certification keyword overlap")
        for keyword in certification_overlap[:2]:
            _append_unique(strongest_alignment, f"{_humanize_keyword(keyword)} certification", limit=5)
    elif matchmaking_profile["certification_keywords"]:
        weak_alignment.append("No matching certification found")

    status_value = (contract.status or "").strip().lower()
    if status_value in {"active", "yes", "reviewing", "drafting", "submitted"}:
        match_breakdown["timeline"] = TIMELINE_MAX_POINTS
    elif status_value:
        weak_alignment.append("Opportunity status may not be active")
    else:
        match_breakdown["timeline"] = round(TIMELINE_MAX_POINTS * 0.5)

    similarity = None
    if profile_embedding:
        contract_embedding = _get_embedding(contract_text)
        similarity = _cosine_similarity(profile_embedding, contract_embedding)
        match_breakdown["embedding"] = _embedding_points(similarity)
        if match_breakdown["embedding"] >= round(EMBEDDING_MAX_POINTS * 0.45):
            _append_unique(strongest_alignment, "Semantic capability match")
        elif match_breakdown["embedding"] == 0:
            weak_alignment.append("Low semantic similarity")

    evidence_score = (
        match_breakdown["embedding"]
        + match_breakdown["naics"]
        + match_breakdown["capabilities"]
        + match_breakdown["certifications"]
    )
    score = _clamp(sum(match_breakdown.values()), 0, 100)

    if not strongest_alignment and score > 0:
        _append_unique(strongest_alignment, "General opportunity fit")

    weak_alignment = weak_alignment[:3]

    return {
        "contract": contract,
        "match_score": score,
        "match_reasons": reasons,
        "match_percentage": int(score),
        "strongest_alignment": strongest_alignment[:10],
        "weak_alignment": weak_alignment,
        "match_breakdown": match_breakdown,
        "keyword_overlap": keyword_overlap,
        "certification_overlap": certification_overlap,
        "embedding_similarity": similarity,
        "has_match_evidence": evidence_score > 0,
    }


def get_matched_contracts_for_user(user, queryset=None):
    matchmaking_profile = get_user_matchmaking_profile(user)
    if not matchmaking_profile["has_matchable_data"]:
        return []

    profile_embedding = _get_embedding(matchmaking_profile["profile_text"])
    contracts = queryset if queryset is not None else Contract.objects.all().order_by("deadline", "-created_at")
    scored_matches = []

    for contract in contracts:
        scored = _score_contract(contract, matchmaking_profile, profile_embedding=profile_embedding)
        if scored["has_match_evidence"]:
            scored_matches.append(scored)

    scored_matches.sort(
        key=lambda item: (
            -item["match_percentage"],
            item["contract"].deadline is None,
            item["contract"].deadline,
            -item["contract"].created_at.timestamp() if item["contract"].created_at else 0,
        )
    )
    return scored_matches
