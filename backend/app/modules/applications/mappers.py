from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.models import Lead
from backend.app.modules.leads.normalizer import resolve_b2b_inquiry_company_name

from .schemas import ApplicationContactOut, ApplicationOut, ApplicationStatus, ApplicationTabBucket

TERMINAL_RECRUITMENT_STATUSES = frozenset(
    {"lost", "rejected", "archived", "spam", "duplicate", "duplicated", "closed"}
)

SOURCE_LABELS: Dict[str, str] = {
    "meta": "Meta Ads",
    "google": "Google Ads",
    "website": "Сайт",
    "linkedin": "LinkedIn",
    "referral": "Рекомендация",
}

SERVICE_LABELS: Dict[str, str] = {
    "targeting_ads": "Таргетинг",
    "recruitment": "Подбор персонала",
    "outsourcing": "Аутсорсинг",
    "legalization": "Легализация",
    "fleet": "Fleet",
}


def _record(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _source_label(raw: Optional[str]) -> Optional[str]:
    key = _text(raw).lower()
    if not key:
        return None
    return SOURCE_LABELS.get(key, raw)


def _sales_service_label(lead: Lead) -> Optional[str]:
    normalized = _record(getattr(lead, "normalized", None))
    need = _record(normalized.get("need"))
    raw = _text(need.get("what_needed")).lower()
    if "таргет" in raw or "target" in raw:
        return "Таргетинг"
    if "подбор" in raw or "водител" in raw or "driver" in raw:
        return "Подбор персонала"
    if "аутсорс" in raw:
        return "Аутсорсинг"
    return None


def _sales_contact(lead: Lead) -> ApplicationContactOut:
    normalized = _record(getattr(lead, "normalized", None))
    contact = _record(normalized.get("contact_person"))
    name = (
        _text(contact.get("full_name"))
        or " ".join(filter(None, [_text(contact.get("first_name")), _text(contact.get("last_name"))])).strip()
        or _text(normalized.get("full_name"))
        or _text(getattr(lead, "full_name", None))
        or "Контакт"
    )
    phone = _text(contact.get("phone")) or _text(normalized.get("phone")) or _text(getattr(lead, "phone", None)) or None
    email = _text(contact.get("email")) or _text(normalized.get("email")) or _text(getattr(lead, "email", None)) or None
    return ApplicationContactOut(name=name, phone=phone, email=email)


def _recruitment_contact(lead: Lead) -> ApplicationContactOut:
    normalized = _record(getattr(lead, "normalized", None))
    name = (
        _text(normalized.get("full_name"))
        or " ".join(filter(None, [_text(normalized.get("first_name")), _text(normalized.get("last_name"))])).strip()
        or _text(normalized.get("phone"))
        or _text(normalized.get("email"))
        or "Кандидат"
    )
    phone = _text(normalized.get("phone")) or _text(getattr(lead, "phone", None)) or None
    email = _text(normalized.get("email")) or _text(getattr(lead, "email", None)) or None
    return ApplicationContactOut(name=name, phone=phone, email=email)


def _sales_status(lead: Lead) -> ApplicationStatus:
    if (
        getattr(lead, "converted_client_id", None)
        or getattr(lead, "client_account_id", None)
        or _text(getattr(lead, "stage", None)).lower() in ("converted", "lost")
    ):
        return "completed"
    normalized = _record(getattr(lead, "normalized", None))
    q_status = _text(normalized.get("sales_questionnaire_status")).lower()
    stage = _text(getattr(lead, "stage", None)).lower()
    if stage == "questionnaire_submitted" or q_status == "submitted":
        return "questionnaire_submitted"
    if stage == "waiting_for_response" or q_status in {"sent", "opened", "in_progress"}:
        return "waiting"
    if not stage or stage == "new":
        return "new"
    if stage == "qualified":
        return "waiting"
    return "in_progress"


def _recruitment_status(lead: Lead) -> ApplicationStatus:
    if getattr(lead, "candidate_id", None):
        return "completed"
    status = _text(getattr(lead, "status", None)).lower()
    if status in TERMINAL_RECRUITMENT_STATUSES:
        return "rejected"
    if not status or status == "new":
        return "new"
    return "in_progress"


def _tab_bucket(status: ApplicationStatus) -> ApplicationTabBucket:
    if status == "rejected":
        return "completed"
    if status == "questionnaire_submitted":
        return "in_progress"
    return status  # type: ignore[return-value]


def _sales_application_from_lead(
    lead: Lead,
    *,
    product_id: str,
    sales_inquiry_id: Optional[str] = None,
    transport_lead_id: Optional[str] = None,
) -> ApplicationOut:
    """Build Sales ApplicationOut from transport Lead display fields."""
    normalized = _record(getattr(lead, "normalized", None))
    company_name = resolve_b2b_inquiry_company_name(
        normalized,
        lead_company_name=_text(getattr(lead, "company_name", None)) or None,
    )
    service = _sales_service_label(lead)
    subtitle = f"Запрос на {service.lower()}" if service else _text(_record(normalized.get("need")).get("summary")) or "B2B заявка"
    status = _sales_status(lead)
    converted_company = _text(getattr(lead, "converted_client_id", None)) or None
    client_account_id = _text(getattr(lead, "client_account_id", None)) or None
    outcome_id = client_account_id or converted_company
    outcome_type = "client_account" if client_account_id else ("client" if converted_company else None)
    queue_bucket = _sales_queue_bucket(lead)
    questionnaire_status = _text(normalized.get("sales_questionnaire_status")) or None
    field_answers = normalized.get("field_answers") if isinstance(normalized.get("field_answers"), list) else []
    additional_answers = (
        normalized.get("additional_answers") if isinstance(normalized.get("additional_answers"), list) else []
    )
    lead_id = _text(getattr(lead, "id", None)) or None
    return ApplicationOut(
        id=str(product_id),
        module="sales",
        contact=_sales_contact(lead),
        title=company_name,
        subtitle=subtitle or None,
        source=_source_label(getattr(lead, "source", None)),
        status=status,
        tab_bucket=_tab_bucket(status),
        assignee_id=_text(getattr(lead, "assigned_to", None)) or _text(getattr(lead, "recruiter_id", None)) or None,
        next_action=_text(getattr(lead, "next_action_type", None)) or None,
        last_activity_at=getattr(lead, "updated_at", None),
        created_at=getattr(lead, "created_at", None),
        priority=_text(getattr(lead, "priority", None)) or None,
        tags=[],
        extensions={
            "service_label": service,
            "company_name": company_name,
            "workflow_step": _sales_workflow_step(lead),
            "client_account_id": client_account_id,
            "company_id": converted_company,
            "sales_queue_bucket": queue_bucket,
            "questionnaire_status": questionnaire_status,
            "questionnaire_summary": _sales_questionnaire_summary(normalized),
            "meta_form_answers": field_answers,
            "additional_answers": additional_answers,
            "raw_payload_stored": bool(getattr(lead, "payload", None)),
            "sales_inquiry_id": sales_inquiry_id,
            "transport_lead_id": transport_lead_id or lead_id,
        },
        outcome_entity_id=outcome_id,
        outcome_entity_type=outcome_type,
        sales_inquiry_id=sales_inquiry_id,
        transport_lead_id=transport_lead_id or lead_id,
    )


def lead_to_sales_inquiry(lead: Lead) -> ApplicationOut:
    """LEGACY PROJECTION — Lead-keyed id. Prefer ``sales_inquiry_to_application`` for product API."""
    lid = str(lead.id)
    return _sales_application_from_lead(lead, product_id=lid, transport_lead_id=lid)


def sales_inquiry_to_application(inquiry: Any, lead: Lead) -> ApplicationOut:
    """Stage 3 slice 3 product projection: ApplicationOut.id = SalesInquiry id."""
    sid = str(getattr(inquiry, "id", "") or "").strip()
    if not sid:
        raise ValueError("sales_inquiry.id is required")
    return _sales_application_from_lead(
        lead,
        product_id=sid,
        sales_inquiry_id=sid,
        transport_lead_id=str(lead.id),
    )


def _sales_workflow_step(lead: Lead) -> int:
    if getattr(lead, "converted_client_id", None) or getattr(lead, "client_account_id", None):
        return 4
    stage = _text(getattr(lead, "stage", None)).lower()
    if stage == "qualified":
        return 3
    if stage in {"waiting_for_response", "questionnaire_submitted"}:
        return 3
    if stage == "contacted":
        return 2
    return 1


def _sales_queue_bucket(lead: Lead) -> str:
    """Operational sales queue key for /app/sales tabs."""
    normalized = _record(getattr(lead, "normalized", None))
    q_status = _text(normalized.get("sales_questionnaire_status")).lower()
    stage = _text(getattr(lead, "stage", None)).lower()
    if getattr(lead, "converted_client_id", None) or getattr(lead, "client_account_id", None) or stage == "converted":
        return "won"
    if stage == "lost":
        return "lost"
    if q_status == "submitted":
        return "questionnaire_submitted"
    if q_status in {"sent", "in_progress"}:
        return "questionnaire_sent"
    meta = _record(normalized.get("meta"))
    next_action = _text(getattr(lead, "next_action_type", None)).lower()
    if _text(meta.get("sales_meeting_scheduled")).lower() in {"1", "true", "yes"} or next_action == "meeting_scheduled":
        return "meeting_scheduled"
    if _text(meta.get("sales_proposal_sent")).lower() in {"1", "true", "yes"} or next_action == "proposal_sent":
        return "proposal_sent"
    if stage == "qualified":
        return "waiting"
    if stage == "contacted":
        return "in_progress"
    return "new"


def _sales_questionnaire_summary(normalized: Dict[str, Any]) -> Dict[str, Any]:
    block = _record(normalized.get("sales_questionnaire"))
    if not block:
        return {}
    return {
        "need_type_label": _text(block.get("need_type_label") or block.get("need_type")) or None,
        "primary_outcome_label": _text(block.get("primary_outcome_label") or block.get("goal_label")) or None,
        "monthly_ad_budget_label": _text(block.get("monthly_ad_budget_label") or block.get("monthly_ad_budget")) or None,
        "start_timeline_label": _text(block.get("start_timeline_label") or block.get("start_timeline")) or None,
        "prior_ads_experience_label": _text(block.get("prior_ads_experience_label") or block.get("prior_ads_experience")) or None,
        "materials_label": _text(block.get("materials_label") or block.get("materials")) or None,
        "decision_maker_label": _text(block.get("decision_maker_label") or block.get("decision_maker")) or None,
    }


def lead_to_recruitment_application(lead: Lead) -> ApplicationOut:
    """LEGACY PROJECTION (Runtime Split R4 — deprecate for R6).

    Maps Lead → ApplicationOut for current Recruitment inbox API.
    SoT after R4 is ``RecruitmentApplication`` table rows, not Lead.
    """
    normalized = _record(getattr(lead, "normalized", None))
    contact = _recruitment_contact(lead)
    subtitle = (
        _text(normalized.get("vacancy_hint"))
        or _text(normalized.get("position"))
        or _text(normalized.get("vacancy_title"))
        or _text(getattr(lead, "vacancy_title", None))
        or _source_label(getattr(lead, "source", None))
        or "Новый отклик"
    )
    status = _recruitment_status(lead)
    candidate_id = _text(getattr(lead, "candidate_id", None)) or None
    vacancy_id = _text(getattr(lead, "vacancy_id", None)) or None
    meta = _record(normalized.get("meta"))
    assignee = (
        _text(meta.get("assigned_manager_id"))
        or _text(getattr(lead, "assigned_to", None))
        or _text(getattr(lead, "recruiter_id", None))
        or None
    )
    return ApplicationOut(
        id=str(lead.id),
        module="recruitment",
        contact=contact,
        title=contact.name,
        subtitle=subtitle,
        source=_source_label(getattr(lead, "source", None)),
        status=status,
        tab_bucket=_tab_bucket(status),
        assignee_id=assignee,
        next_action=_text(getattr(lead, "next_action_type", None)) or None,
        last_activity_at=getattr(lead, "updated_at", None),
        created_at=getattr(lead, "created_at", None),
        priority=_text(getattr(lead, "priority", None)) or None,
        tags=[],
        extensions={
            "vacancy_id": vacancy_id,
            "vacancy_title": _text(getattr(lead, "vacancy_title", None)) or _text(normalized.get("vacancy_title")) or None,
            "fit_status": _text(getattr(lead, "fit_status", None)) or None,
        },
        outcome_entity_id=candidate_id,
        outcome_entity_type="candidate" if candidate_id else None,
    )


def is_open_recruitment_application(lead: Lead) -> bool:
    if getattr(lead, "candidate_id", None):
        return False
    if _text(getattr(lead, "lead_type", None)) == "client" and _text(getattr(lead, "lead_target_type", None)) == "client_lead":
        return False
    status = _text(getattr(lead, "status", None)).lower()
    return status not in TERMINAL_RECRUITMENT_STATUSES


def is_recruitment_inbox_application(lead: Lead, *, scope: str = "all") -> bool:
    """Recruitment inbox row filter. ``open`` = pending only; ``all`` includes completed/rejected."""
    if _text(getattr(lead, "lead_type", None)) == "client" and _text(getattr(lead, "lead_target_type", None)) == "client_lead":
        return False
    if scope == "open":
        return is_open_recruitment_application(lead)
    if is_open_recruitment_application(lead):
        return True
    if getattr(lead, "candidate_id", None):
        return True
    status = _text(getattr(lead, "status", None)).lower()
    return status in TERMINAL_RECRUITMENT_STATUSES
