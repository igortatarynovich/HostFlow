"""
Single evaluator for vacancy.lead_criteria_v1 vs lead.normalized (§2.10 / §2.5).

Used by list/get leads (display) and process_normalized_lead (routing / automatic gating).
Do not duplicate criteria logic elsewhere — extend here only.
"""

from __future__ import annotations

from typing import Any, Collection, List, Mapping, Optional, Set, Tuple

from backend.app.services.document_catalog import normalize_doc_type

# Align with LeadFitStatus in schemas.py
FitResult = Tuple[str, List[str]]

# Acceptable Document.status values for lead routing when vacancy does not override.
DEFAULT_CANDIDATE_DOCUMENT_OK_STATUSES: frozenset[str] = frozenset(
    {
        "completed",
        "approved",
        "verified",
        "delivered",
        "received",
        "issued",
        "active",
        "registered",
    }
)


def evaluate_lead_criteria_v1(
    normalized: Any,
    criteria: Any,
    *,
    candidate_document_statuses: Optional[Mapping[str, Collection[str]]] = None,
) -> FitResult:
    """
    MVP vacancy fit evaluator.

    criteria schema (lead_criteria_v1), typically from Vacancy.extra:
      - min_experience_eu_years: int
      - requires_fields: [string]            # normalized keys required to be present (truthy)
      - in_poland: bool                      # requires normalized.in_poland == True/False
      - requires_documents: [string]         # requires normalized.documents includes each code
      - requires_candidate_documents_v1: [string]  # doc_type codes vs Documents module (see below)
      - candidate_documents_allow_statuses: [string]  # optional whitelist of Document.status (lowercase)
      - allowed_countries: [string]          # ISO2; if set, normalized.country must match (case-insensitive)
      - blocked_countries: [string]          # ISO2; if country in list → no_fit
      - allowed_geo_countries: [string]      # §2.5: location vs citizenship — first hit among normalized.geo_country,
                                              # location_country, current_country must match (same rules as allowed_countries)
      - blocked_geo_countries: [string]      # if lead geo country in list → no_fit
      - required_nationality: string       # must match normalized.nationality or nationality_code (case-insensitive)
      - requires_languages_any: [string]     # at least one must appear in normalized.languages[] or normalized.language

    candidate_document_statuses: when ``requires_candidate_documents_v1`` is set, map canonical doc_type ->
    collection of status strings for that candidate (from ``documents`` table). ``None`` means no linked
    candidate / context not loaded → ``needs_info`` with ``documents_module_no_candidate``.

    Returns:
      ("no_criteria", []) — empty criteria → treat as universal match in routing.
      ("fit", []) — all checks pass.
      ("needs_info", reasons) — missing data; operator may collect more fields.
      ("no_fit", reasons) — hard mismatch.
    """
    if not isinstance(criteria, dict) or not criteria:
        return ("no_criteria", [])
    norm = normalized if isinstance(normalized, dict) else {}
    reasons: list[str] = []
    missing_info = False
    hard_fail = False

    min_years = criteria.get("min_experience_eu_years")
    if min_years is not None:
        try:
            min_years_i = int(min_years)
        except Exception:
            min_years_i = 0
        if min_years_i > 0:
            value = norm.get("experience_eu_years")
            if value is None:
                missing_info = True
                reasons.append("missing_experience_eu_years")
            else:
                try:
                    years_i = int(value)
                except Exception:
                    years_i = -1
                if years_i < min_years_i:
                    reasons.append(f"experience_eu_years<{min_years_i}")
                    hard_fail = True

    req_fields = criteria.get("requires_fields")
    if isinstance(req_fields, list):
        for key in req_fields:
            k = str(key or "").strip()
            if not k:
                continue
            if not norm.get(k):
                missing_info = True
                reasons.append(f"missing:{k}")

    in_poland_req = criteria.get("in_poland")
    if isinstance(in_poland_req, bool):
        value = norm.get("in_poland")
        if value is None:
            missing_info = True
            reasons.append("missing_in_poland")
        else:
            if bool(value) is not in_poland_req:
                reasons.append(f"in_poland!={str(in_poland_req).lower()}")
                hard_fail = True

    req_docs = criteria.get("requires_documents")
    if isinstance(req_docs, list):
        docs = norm.get("documents")
        docs_set = set()
        if isinstance(docs, list):
            docs_set = {str(x).strip().lower() for x in docs if str(x or "").strip()}
        for code in req_docs:
            c = str(code or "").strip().lower()
            if not c:
                continue
            if not docs_set:
                missing_info = True
                reasons.append("missing_documents")
                break
            if c not in docs_set:
                reasons.append(f"missing_doc:{c}")
                hard_fail = True

    def _norm_country(val: Any) -> str:
        return str(val or "").strip().upper()

    allowed = criteria.get("allowed_countries")
    if isinstance(allowed, list) and allowed:
        allow_set = {_norm_country(x) for x in allowed if _norm_country(x)}
        if allow_set:
            cc = _norm_country(norm.get("country"))
            if not cc:
                missing_info = True
                reasons.append("missing_country")
            elif cc not in allow_set:
                reasons.append(f"country_not_in_allowed:{cc}")
                hard_fail = True

    blocked = criteria.get("blocked_countries")
    if isinstance(blocked, list) and blocked:
        block_set = {_norm_country(x) for x in blocked if _norm_country(x)}
        cc = _norm_country(norm.get("country"))
        if cc and cc in block_set:
            reasons.append(f"country_blocked:{cc}")
            hard_fail = True

    def _lead_geo_country(norm_d: Mapping[str, Any]) -> str:
        for key in ("geo_country", "location_country", "current_country"):
            v = norm_d.get(key)
            cc = _norm_country(v)
            if cc:
                return cc
        return ""

    allowed_geo = criteria.get("allowed_geo_countries")
    if isinstance(allowed_geo, list) and allowed_geo:
        geo_allow = {_norm_country(x) for x in allowed_geo if _norm_country(x)}
        if geo_allow:
            gcc = _lead_geo_country(norm)
            if not gcc:
                missing_info = True
                reasons.append("missing_geo_country")
            elif gcc not in geo_allow:
                reasons.append(f"geo_country_not_in_allowed:{gcc}")
                hard_fail = True

    blocked_geo = criteria.get("blocked_geo_countries")
    if isinstance(blocked_geo, list) and blocked_geo:
        geo_block = {_norm_country(x) for x in blocked_geo if _norm_country(x)}
        if geo_block:
            gcc = _lead_geo_country(norm)
            if gcc and gcc in geo_block:
                reasons.append(f"geo_country_blocked:{gcc}")
                hard_fail = True

    nat_req = criteria.get("required_nationality")
    if nat_req is not None and str(nat_req).strip():
        want = str(nat_req).strip().lower()
        got = norm.get("nationality") or norm.get("nationality_code")
        got_s = str(got or "").strip().lower()
        if not got_s:
            missing_info = True
            reasons.append("missing_nationality")
        elif got_s != want:
            reasons.append(f"nationality_mismatch:{got_s}")
            hard_fail = True

    langs_req = criteria.get("requires_languages_any")
    if isinstance(langs_req, list) and langs_req:
        want = {str(x).strip().lower() for x in langs_req if str(x or "").strip()}
        lead_langs: set[str] = set()
        raw_lang = norm.get("language")
        if isinstance(raw_lang, str) and raw_lang.strip():
            lead_langs.add(raw_lang.strip().lower())
        raw_list = norm.get("languages")
        if isinstance(raw_list, list):
            for x in raw_list:
                s = str(x or "").strip().lower()
                if s:
                    lead_langs.add(s)
        if not lead_langs:
            missing_info = True
            reasons.append("missing_languages")
        elif not (want & lead_langs):
            reasons.append("languages_no_overlap")
            hard_fail = True

    mod_req = criteria.get("requires_candidate_documents_v1")
    if isinstance(mod_req, list) and mod_req:
        allow_raw = criteria.get("candidate_documents_allow_statuses")
        if isinstance(allow_raw, list) and allow_raw:
            allow: Set[str] = {str(x).strip().lower() for x in allow_raw if str(x or "").strip()}
        else:
            allow = set(DEFAULT_CANDIDATE_DOCUMENT_OK_STATUSES)

        if candidate_document_statuses is None:
            missing_info = True
            reasons.append("documents_module_no_candidate")
        else:
            cmap: dict[str, set[str]] = {}
            for dt, sts in candidate_document_statuses.items():
                ck = normalize_doc_type(str(dt))
                if ck not in cmap:
                    cmap[ck] = set()
                for s in sts:
                    cmap[ck].add(str(s).strip().lower())

            for raw_code in mod_req:
                ck = normalize_doc_type(str(raw_code or ""))
                if not ck or ck == "additional_document":
                    continue
                present = cmap.get(ck, set())
                if not present:
                    missing_info = True
                    reasons.append(f"candidate_doc_missing:{ck}")
                elif not (present & allow):
                    worst = sorted(present)[0]
                    reasons.append(f"candidate_doc_status_blocked:{ck}:{worst}")
                    hard_fail = True

    if reasons:
        if hard_fail:
            return ("no_fit", reasons)
        if missing_info:
            return ("needs_info", reasons)
        return ("no_fit", reasons)
    return ("fit", [])


def criteria_from_vacancy_extra(vacancy_extra: Any) -> Any:
    """Read lead_criteria_v1 from Vacancy.extra (JSON / dict)."""
    if not vacancy_extra:
        return None
    if isinstance(vacancy_extra, dict):
        return vacancy_extra.get("lead_criteria_v1")
    try:
        import json

        obj = json.loads(str(vacancy_extra))
        if isinstance(obj, dict):
            return obj.get("lead_criteria_v1")
    except Exception:
        pass
    return None


def evaluate_vacancy_for_lead(
    normalized: Any,
    vacancy_extra: Any,
    *,
    candidate_document_statuses: Optional[Mapping[str, Collection[str]]] = None,
) -> FitResult:
    """Convenience: extra JSON → criteria → evaluate."""
    return evaluate_lead_criteria_v1(
        normalized,
        criteria_from_vacancy_extra(vacancy_extra),
        candidate_document_statuses=candidate_document_statuses,
    )


def ordered_vacancy_ids_from_tenant_settings(settings: Any) -> list[str]:
    """
    Tenant.settings['lead_fit_routing_v1'] = { "ordered_vacancy_ids": ["uuid", ...] }
    First matching vacancy (fit or no_criteria) wins when ad/id mapping is absent.
    """
    if not isinstance(settings, dict):
        return []
    raw = settings.get("lead_fit_routing_v1")
    if not isinstance(raw, dict):
        return []
    ids = raw.get("ordered_vacancy_ids")
    if not isinstance(ids, list):
        return []
    out: list[str] = []
    for x in ids:
        s = str(x or "").strip()
        if s and s not in out:
            out.append(s)
    return out
