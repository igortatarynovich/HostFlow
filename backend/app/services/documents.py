from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Tuple

from .document_applicability_policy import derive_document_applicability_decision
from .config_loader import load_config
from .document_hub_delivery_contract import list_canonical_document_type_codes_via_contract
from .reference_service_facade import ReferenceServiceFacade

ISO = "%Y-%m-%d"

DocStatus = Literal["planned", "pending_validation", "verified", "invalid", "expired"]


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    return datetime.strptime(s[:10], ISO)


def _fmt_date(d: Optional[datetime]) -> Optional[str]:
    return d.strftime(ISO) if d else None


def _get_extra(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return candidate.get("extra") or {}


def _set_extra(candidate: Dict[str, Any], extra: Dict[str, Any]) -> None:
    candidate["extra"] = extra


def _ensure_docs(extra: Dict[str, Any]) -> List[Dict[str, Any]]:
    docs = extra.get("documents")
    if not isinstance(docs, list):
        docs = []
        extra["documents"] = docs
    return docs


def _get_doc(docs: List[Dict[str, Any]], code: str) -> Optional[Dict[str, Any]]:
    for d in docs:
        if isinstance(d, dict) and d.get("code") == code:
            return d
    return None


def auto_apply_rules(candidate_row: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Проставляет:
     - work_permit_type (oswiadczenie/zezwolenie_A)
     - visa_required
     - добавляет пустые карточки блокирующих документов в extra.documents со статусом planned
    Возвращает обновлённый extra и список доков, что были добавлены.
    """
    rules: Dict[str, Any] = load_config("citizenship_rules.json")

    canonical_doc_codes = list_canonical_document_type_codes_via_contract()

    # reminders config not used here; removed to satisfy linter

    eu = set(rules.get("eu_eea_ch", []))
    osw_list = set(rules.get("oswiadczenie_list", []))

    extra = _get_extra(candidate_row)
    docs = _ensure_docs(extra)

    citizenship = ReferenceServiceFacade.normalize_citizenship_alpha2(
        str(extra.get("citizenship") or candidate_row.get("citizenship") or "")
    ) or ""
    role = (extra.get("role") or candidate_row.get("role") or "driver").lower()
    work_country = ReferenceServiceFacade.normalize_country_alpha2(
        str(extra.get("work_country") or candidate_row.get("work_country") or "")
    ) or "PL"

    applicability = derive_document_applicability_decision(
        citizenship=citizenship,
        work_country=work_country,
        role=role,
        eu_countries=eu,
        oswiadczenie_countries=osw_list,
    )
    wpt = applicability.work_permit_type

    if not extra.get("manual_override"):
        extra["work_permit_type"] = wpt
    else:
        extra.setdefault("work_permit_type", wpt)

    # visa_required
    visa_required = applicability.visa_required
    if not extra.get("manual_override"):
        extra["visa_required"] = visa_required
    else:
        extra.setdefault("visa_required", visa_required)

    added: List[str] = []

    # обязательные блокирующие документы
    def ensure_doc(code: str) -> None:
        if code not in canonical_doc_codes:
            return
        if not _get_doc(docs, code):
            docs.append(
                {
                    "code": code,
                    "status": "planned",
                    "manual_override": False,
                }
            )
            added.append(code)

    # если нужен пермит
    if extra.get("work_permit_type") in ("oswiadczenie", "zezwolenie_A"):
        ensure_doc(extra["work_permit_type"])  # type: ignore[index]

    # если нужна виза
    if extra.get("visa_required"):
        ensure_doc("visa_D")
        v = _get_doc(docs, "visa_D")
        if v and not v.get("based_on"):
            v["based_on"] = extra.get("work_permit_type")

    # водитель-не ЕС → świadectwo_kierowcy
    if applicability.driver_attestation_required:
        ensure_doc("swiadectwo_kierowcy")

    # Базовый набор блокирующих документов
    for base in (
        "prawo_jazdy",
        "karta_tachografu",
        "passport",
        "umowa_o_prace",
        "badania_lekarskie",
    ):
        ensure_doc(base)

    _set_extra(candidate_row, extra)
    return extra, added


def predict_ready_date(doc: Dict[str, Any], extra: Dict[str, Any]) -> Optional[str]:
    """
    На основании SLA конфигов возвращает predicted_issue_date, если нет фактической.
    """
    code = doc.get("code")
    status: DocStatus = doc.get("status", "planned")  # type: ignore[assignment]
    if status == "verified" and doc.get("issue_date"):
        return doc.get("issue_date")

    if code in ("oswiadczenie", "zezwolenie_A"):
        wp_cfg_all: Dict[str, Any] = load_config("sla_work_permit.json")
        wp_cfg: Dict[str, Any] = wp_cfg_all.get(code, {})
        base = _parse_date(doc.get("submitted_at") or doc.get("submission_date"))
        if not base:
            base = datetime.utcnow()
        days = int(wp_cfg.get("default_issue_days", 14))
        place = (doc.get("place") or "").lower()
        voiv_map: Dict[str, int] = wp_cfg.get("by_voivodeship_days", {})
        for k, v in voiv_map.items():
            if k in place:
                days = int(v)
                break
        return _fmt_date(base + timedelta(days=days))

    if code == "visa_D":
        visa_cfg_all: Dict[str, Any] = load_config("sla_visa.json")
        visa_cfg: Dict[str, Any] = visa_cfg_all.get("visa_D", {})
        mode = doc.get("submission_mode") or "in_person"
        avg = visa_cfg.get("submission_modes", {}).get(mode, {}).get("avg_days") or visa_cfg.get(
            "default_avg_days", 21
        )
        base = _parse_date(doc.get("submission_date"))
        if not base:
            based_on = doc.get("based_on")
            if based_on:
                base = datetime.utcnow()
        if not base:
            base = datetime.utcnow()
        return _fmt_date(base + timedelta(days=int(avg)))

    if code == "swiadectwo_kierowcy":
        att_cfg_all: Dict[str, Any] = load_config("sla_driver_attestation.json")
        att_cfg: Dict[str, Any] = att_cfg_all.get("swiadectwo_kierowcy", {})
        base = _parse_date(doc.get("submission_date")) or datetime.utcnow()
        return _fmt_date(base + timedelta(days=int(att_cfg.get("default_issue_days", 21))))

    if code == "karta_tachografu":
        base = _parse_date(doc.get("submission_date")) or datetime.utcnow()
        return _fmt_date(base + timedelta(days=14))

    return None


def recompute_eta(candidate_row: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    eta_trip = max(готовые_или_прогноз) по блокирующим
    eta_invoice — по конфигу business model, если не задан — = eta_trip
    """
    eta_rules: Dict[str, Any] = load_config("eta_rules.json")

    extra = _get_extra(candidate_row)
    docs = _ensure_docs(extra)

    def ready_or_pred(code: str) -> Optional[datetime]:
        d = _get_doc(docs, code)
        if not d:
            return None
        dt = _parse_date(d.get("issue_date") or d.get("predicted_issue_date"))
        if dt:
            return dt
        pred = predict_ready_date(d, extra)
        if pred:
            d["predicted_issue_date"] = pred
            return _parse_date(pred)
        return None

    block = eta_rules.get("blocking_docs_for_trip", [])
    dates_list: List[datetime] = []
    for c in block:
        dt = ready_or_pred(c)
        if dt is not None:
            dates_list.append(dt)
    eta_trip = max(dates_list).strftime(ISO) if dates_list else None
    extra["eta_trip"] = eta_trip

    biz = extra.get("invoice_model") or "pay_on_trip"
    if biz == "pay_on_trip":
        eta_invoice = eta_trip
    elif biz == "pay_on_hire":
        doc_row = _get_doc(docs, "umowa_o_prace")
        eta_invoice = doc_row.get("sign_date") if doc_row else None
    elif biz == "pay_on_docs_package":
        trio = ["oswiadczenie", "zezwolenie_A", "visa_D"]
        dd_list: List[datetime] = []
        for c in trio:
            d2 = ready_or_pred(c)
            if d2 is not None:
                dd_list.append(d2)
        eta_invoice = max(dd_list).strftime(ISO) if dd_list else None
    else:
        eta_invoice = eta_trip

    extra["eta_invoice"] = eta_invoice
    return eta_trip, eta_invoice
