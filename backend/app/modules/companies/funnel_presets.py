"""
Default funnel stage trees for tenant bootstrap: by business profile (agency / employer / services)
and optional industry from onboarding (`settings.onboarding.industry` or operating `Company.extra.industry`).

Industry keys align with `OnboardingCompanyPage` / OwnCompany `extra.industry`.
"""

from __future__ import annotations

from typing import Any

# Must match hostflow-frontend OnboardingCompanyPage IndustryKey
INDUSTRY_KEYS = frozenset(
    {
        "transport_logistics",
        "construction",
        "horeca",
        "healthcare",
        "it",
        "manufacturing",
        "other",
    }
)

StageRow = tuple[str, str, str, bool]


def normalize_industry(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip().lower().replace("-", "_")
    return s if s in INDUSTRY_KEYS else None


def _base_candidate_presets() -> dict[str, dict[str, Any]]:
    return {
        "agency": {
            "name": "Candidate Pipeline",
            "stages": [
                ("new", "New", "new", False),
                ("contacted", "Contacted", "in_progress", False),
                ("waiting_docs", "Waiting for documents", "in_progress", False),
                ("docs_received", "Documents received", "in_progress", False),
                ("ready_client", "Ready for client", "in_progress", False),
                ("handoff", "Handoff", "in_progress", False),
                ("hired", "Hired", "hired", True),
                ("rejected", "Rejected", "declined_rejected", True),
            ],
        },
        "employer": {
            "name": "Hiring Pipeline",
            "stages": [
                ("new", "New", "new", False),
                ("screening", "Screening", "in_progress", False),
                ("interview", "Interview", "in_progress", False),
                ("offer", "Offer", "in_progress", False),
                ("hired", "Hired", "hired", True),
                ("rejected", "Rejected", "declined_rejected", True),
            ],
        },
    }


def _base_lead_presets() -> dict[str, dict[str, Any]]:
    return {
        "agency": {
            "name": "Lead Pipeline",
            "stages": [
                ("new", "New", "new", False),
                ("contacted", "Contact made", "in_progress", False),
                ("qualified", "Qualified", "in_progress", False),
                ("converted", "Converted", "hired", True),
                ("lost", "Lost", "declined_rejected", True),
            ],
        },
        "services": {
            "name": "Service Sales Pipeline",
            "stages": [
                ("new", "New lead", "new", False),
                ("contacted", "Contacted", "in_progress", False),
                ("proposal", "Proposal", "in_progress", False),
                ("negotiation", "Negotiation", "in_progress", False),
                ("won", "Won", "hired", True),
                ("lost", "Lost", "declined_rejected", True),
            ],
        },
    }


def _candidate_industry_override(company_type: str, industry: str) -> dict[str, Any] | None:
    if company_type == "agency" and industry == "transport_logistics":
        return {
            "name": "Candidate pipeline — transport & compliance",
            "stages": [
                ("new", "New", "new", False),
                ("contacted", "Contacted", "in_progress", False),
                ("questionnaire_submitted", "Pre-screen", "in_progress", False),
                ("waiting_docs", "Documents collection", "in_progress", False),
                ("docs_received", "Documents OK", "in_progress", False),
                ("permit_ordered", "Work permit ordered", "in_progress", False),
                ("permit_received", "Permit received", "in_progress", False),
                ("trip_plan", "Arrival planning", "in_progress", False),
                ("ready_client", "Ready for client", "in_progress", False),
                ("handoff", "Handoff", "in_progress", False),
                ("hired", "Hired", "hired", True),
                ("rejected", "Rejected", "declined_rejected", True),
            ],
        }

    if company_type == "agency" and industry == "construction":
        return {
            "name": "Candidate pipeline — construction & permits",
            "stages": [
                ("new", "New", "new", False),
                ("contacted", "Contacted", "in_progress", False),
                ("waiting_docs", "Certs & docs", "in_progress", False),
                ("docs_received", "Documents OK", "in_progress", False),
                ("permit_ordered", "Permits / safety clearance", "in_progress", False),
                ("ready_client", "Ready for site / client", "in_progress", False),
                ("handoff", "Handoff", "in_progress", False),
                ("hired", "Hired", "hired", True),
                ("rejected", "Rejected", "declined_rejected", True),
            ],
        }

    if company_type == "employer" and industry == "healthcare":
        return {
            "name": "Hiring pipeline — healthcare compliance",
            "stages": [
                ("new", "New", "new", False),
                ("screening", "Credentials screening", "in_progress", False),
                ("questionnaire_submitted", "Compliance questionnaire", "in_progress", False),
                ("interview", "Interview", "in_progress", False),
                ("offer", "Offer", "in_progress", False),
                ("hired", "Hired", "hired", True),
                ("rejected", "Rejected", "declined_rejected", True),
            ],
        }

    if company_type == "employer" and industry == "it":
        return {
            "name": "Hiring pipeline — IT",
            "stages": [
                ("new", "New", "new", False),
                ("screening", "Technical screening", "in_progress", False),
                ("interview", "Interview", "in_progress", False),
                ("offer", "Offer", "in_progress", False),
                ("hired", "Hired", "hired", True),
                ("rejected", "Rejected", "declined_rejected", True),
            ],
        }

    if company_type == "employer" and industry == "manufacturing":
        return {
            "name": "Hiring pipeline — manufacturing",
            "stages": [
                ("new", "New", "new", False),
                ("screening", "Screening", "in_progress", False),
                ("docs_wait", "Safety / certifications", "in_progress", False),
                ("interview", "Interview", "in_progress", False),
                ("offer", "Offer", "in_progress", False),
                ("hired", "Hired", "hired", True),
                ("rejected", "Rejected", "declined_rejected", True),
            ],
        }

    if company_type == "employer" and industry == "horeca":
        return {
            "name": "Hiring pipeline — HoReCa",
            "stages": [
                ("new", "New", "new", False),
                ("screening", "Screening", "in_progress", False),
                ("interview", "Interview / trial shift", "in_progress", False),
                ("offer", "Offer", "in_progress", False),
                ("hired", "Hired", "hired", True),
                ("rejected", "Rejected", "declined_rejected", True),
            ],
        }

    return None


def _lead_industry_override(company_type: str, industry: str) -> dict[str, Any] | None:
    if company_type == "agency" and industry == "transport_logistics":
        return {
            "name": "Client pipeline — logistics",
            "stages": [
                ("new", "New lead", "new", False),
                ("contacted", "Contacted", "in_progress", False),
                ("qualified", "Fleet / route fit", "in_progress", False),
                ("converted", "Converted", "hired", True),
                ("lost", "Lost", "declined_rejected", True),
            ],
        }

    if company_type == "services" and industry == "horeca":
        return {
            "name": "Service sales — HoReCa",
            "stages": [
                ("new", "New inquiry", "new", False),
                ("contacted", "Contacted", "in_progress", False),
                ("proposal", "Quote / scope", "in_progress", False),
                ("negotiation", "Terms", "in_progress", False),
                ("won", "Won", "hired", True),
                ("lost", "Lost", "declined_rejected", True),
            ],
        }

    if company_type == "services" and industry == "construction":
        return {
            "name": "Service sales — construction",
            "stages": [
                ("new", "New lead", "new", False),
                ("contacted", "Contacted", "in_progress", False),
                ("proposal", "Bid / proposal", "in_progress", False),
                ("negotiation", "Negotiation", "in_progress", False),
                ("won", "Won", "hired", True),
                ("lost", "Lost", "declined_rejected", True),
            ],
        }

    if company_type == "services" and industry == "it":
        return {
            "name": "Service sales — IT",
            "stages": [
                ("new", "New lead", "new", False),
                ("contacted", "Discovery", "in_progress", False),
                ("proposal", "Proposal / SOW", "in_progress", False),
                ("negotiation", "Negotiation", "in_progress", False),
                ("won", "Won", "hired", True),
                ("lost", "Lost", "declined_rejected", True),
            ],
        }

    return None


def business_funnel_presets(company_type: str | None, industry: str | None = None) -> dict[str, dict[str, Any]]:
    """
    Returns {"candidate": {"name", "stages"}, "lead": {"name", "stages"}}.
    `company_type`: agency | employer | services.
    """
    normalized = str(company_type or "").strip().lower() or "agency"
    if normalized not in ("agency", "employer", "services"):
        normalized = "agency"

    ind = normalize_industry(industry)

    c_presets = _base_candidate_presets()
    l_presets = _base_lead_presets()

    candidate_base = c_presets.get(normalized, c_presets["agency"])
    candidate_row: dict[str, Any] = {"name": str(candidate_base["name"]), "stages": list(candidate_base["stages"])}

    lead_base = l_presets.get(normalized, l_presets["agency"])
    lead_row: dict[str, Any] = {"name": str(lead_base["name"]), "stages": list(lead_base["stages"])}

    if ind and ind != "other":
        if normalized in ("agency", "employer"):
            co = _candidate_industry_override(normalized, ind)
            if co is not None:
                candidate_row = co
        lo = _lead_industry_override(normalized, ind)
        if lo is not None:
            lead_row = lo

    return {
        "candidate": candidate_row,
        "lead": lead_row,
    }
