"""Lead RODO information-obligation evaluation (GDPR art.13 / art.14).

Platform-mandatory: a tenant cannot disable evaluation or fulfillment.
HostFlow is delivery infrastructure; the operating firm (OwnCompany) remains
the controller named in the notice.

Technical invariant: no lead may silently bypass evaluation. An unresolved or
failed obligation stays explicitly actionable until resolved.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping, Optional

CollectionPath = Literal["direct", "indirect", "unknown"]
Article = Literal["13", "14"]
AssessmentState = Literal["compliant", "delivery_required", "exempt", "review_required"]
ComplianceState = Literal[
    "compliant",
    "delivery_required",
    "delivered",
    "exempt",
    "review_required",
    "delivery_failed",
]
ObligationAction = Literal[
    "no_delivery_source_provided",
    "no_delivery_already_notified",
    "no_delivery_exempt",
    "delivery_required",
    "review_required",
]

# Person submitted data themselves (form / lead-ad / bot intake).
_DIRECT_SOURCES = frozenset(
    {
        "meta",
        "meta_ads",
        "facebook",
        "tiktok",
        "google_ads",
        "public_form",
        "public-intake",
        "public_intake",
        "lead_form",
        "telegram_bot",
        "telegram_intake",
        "telegram_intake_completion",
    }
)

# Data not collected from the data subject (import, referral, scrape, dump).
_INDIRECT_SOURCES = frozenset(
    {
        "csv_import",
        "import",
        "webhook",
        "manual",
        "linkedin",
        "excel",
        "referral",
        "third_party",
        "database",
    }
)

_EXEMPT_CODES = frozenset(
    {
        "art_14_5_a",
        "art_14_5_b",
        "art_14_5_c",
        "art_14_5_d",
        "already_has_information",
        "disproportionate_effort",
        "legal_secrecy",
        "legal_obligation",
    }
)

_SATISFIED_STATUSES = frozenset({"sent", "satisfied", "source_provided", "exempt"})
_NEGATIVE_STATUSES = frozenset(
    {
        "failed",
        "deferred",
        "undelivered",
        "pending_channel",
        "pending_policy",
        "review_required",
        "delivery_required",
        "delivery_failed",
    }
)


@dataclass(frozen=True, slots=True)
class ObligationDecision:
    action: ObligationAction
    state: AssessmentState
    article: Optional[Article]
    collection_path: CollectionPath
    reason_code: str
    notice_at_source: bool
    already_notified: bool
    exempt: bool
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "state": self.state,
            "article": self.article,
            "collection_path": self.collection_path,
            "reason_code": self.reason_code,
            "notice_at_source": self.notice_at_source,
            "already_notified": self.already_notified,
            "exempt": self.exempt,
            "source": self.source,
        }

    def assessment_evidence(self, *, evaluated_at: str) -> dict[str, Any]:
        """Why the engine chose art.13 / art.14 / exempt / already provided / review."""
        return {
            "state": self.state,
            "article": self.article,
            "collection_path": self.collection_path,
            "reason_code": self.reason_code,
            "source": self.source,
            "notice_at_source": self.notice_at_source,
            "already_notified": self.already_notified,
            "exempt": self.exempt,
            "evaluated_at": evaluated_at,
        }


def classify_collection_path(source: str) -> CollectionPath:
    s = str(source or "").strip().lower()
    if not s:
        return "unknown"
    if s in _DIRECT_SOURCES or s.startswith("telegram") or s.startswith("public"):
        return "direct"
    if s in _INDIRECT_SOURCES or "import" in s:
        return "indirect"
    return "unknown"


def notice_provided_at_source(normalized: Optional[Mapping[str, Any]]) -> bool:
    """True when intake captured that the person was shown the information notice."""
    if not isinstance(normalized, Mapping):
        return False
    flag = normalized.get("rodo_notice_at_source")
    if flag is True:
        return True
    if isinstance(flag, str) and flag.strip().lower() in ("true", "1", "yes", "on"):
        return True
    nested = normalized.get("consents")
    if isinstance(nested, Mapping):
        rodo = nested.get("rodo") or nested.get("gdpr")
        if rodo is True:
            return True
        if isinstance(rodo, str) and rodo.strip().lower() in ("true", "1", "yes", "accepted"):
            return True
    return False


def _rodo_block(normalized: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(normalized, Mapping):
        return {}
    raw = normalized.get("rodo")
    return dict(raw) if isinstance(raw, Mapping) else {}


def _already_notified(block: Mapping[str, Any]) -> bool:
    st = str(block.get("status") or "").strip().lower()
    if st in _NEGATIVE_STATUSES:
        return False
    if st in ("sent", "satisfied"):
        return True
    return bool(str(block.get("sent_at") or "").strip())


def _exemption_code(normalized: Optional[Mapping[str, Any]], block: Mapping[str, Any]) -> Optional[str]:
    raw = block.get("exemption_code") or (normalized or {}).get("rodo_exempt_code")
    code = str(raw or "").strip().lower()
    if code in _EXEMPT_CODES:
        return code
    return None


def _exemption_claimed_without_reason(
    normalized: Optional[Mapping[str, Any]],
    block: Mapping[str, Any],
) -> bool:
    if _exemption_code(normalized, block):
        return False
    if str(block.get("status") or "").strip().lower() == "exempt":
        return True
    flag = (normalized or {}).get("rodo_exempt") if isinstance(normalized, Mapping) else None
    if flag is True or (isinstance(flag, str) and flag.strip().lower() in ("true", "1", "yes")):
        return True
    raw = block.get("exemption_code") or (normalized or {}).get("rodo_exempt_code")
    return bool(str(raw or "").strip())


def _decision(
    *,
    action: ObligationAction,
    state: AssessmentState,
    article: Optional[Article],
    path: CollectionPath,
    reason_code: str,
    notice: bool,
    already: bool,
    exempt: bool,
    source: str,
) -> ObligationDecision:
    return ObligationDecision(
        action=action,
        state=state,
        article=article,
        collection_path=path,
        reason_code=reason_code,
        notice_at_source=notice,
        already_notified=already,
        exempt=exempt,
        source=str(source or "").strip(),
    )


def evaluate_lead_rodo_obligation(
    *,
    source: str,
    normalized: Optional[Mapping[str, Any]] = None,
) -> ObligationDecision:
    """Decide the information obligation for a recorded lead.

    Always returns a controlled state. Unknown collection path is
    ``review_required``, never a silent no-op.
    """
    src = str(source or "").strip()
    path = classify_collection_path(src)
    article: Optional[Article] = "13" if path == "direct" else ("14" if path == "indirect" else None)
    notice = notice_provided_at_source(normalized)
    block = _rodo_block(normalized)
    exempt_code = _exemption_code(normalized, block)
    already = _already_notified(block)
    source_status = str(block.get("status") or "").strip().lower() == "source_provided"
    kw: dict[str, Any] = {"notice": notice, "already": already, "source": src, "path": path}

    if exempt_code:
        return _decision(
            action="no_delivery_exempt",
            state="exempt",
            article=article,
            reason_code=exempt_code,
            exempt=True,
            **kw,
        )
    if _exemption_claimed_without_reason(normalized, block):
        return _decision(
            action="review_required",
            state="review_required",
            article=article,
            reason_code="exemption_reason_missing",
            exempt=False,
            **kw,
        )
    if already:
        return _decision(
            action="no_delivery_already_notified",
            state="compliant",
            article=article,
            reason_code="already_notified",
            exempt=False,
            **kw,
        )
    if notice or source_status:
        return _decision(
            action="no_delivery_source_provided",
            state="compliant",
            article="13" if path == "direct" or notice else article,
            reason_code="notice_at_source" if notice else "source_provided",
            exempt=False,
            **kw,
        )
    if path == "unknown":
        return _decision(
            action="review_required",
            state="review_required",
            article=None,
            reason_code="collection_path_unknown",
            exempt=False,
            **kw,
        )
    if path == "direct":
        return _decision(
            action="delivery_required",
            state="delivery_required",
            article="13",
            reason_code="direct_collection_notice_unproven",
            exempt=False,
            **kw,
        )
    return _decision(
        action="delivery_required",
        state="delivery_required",
        article="14",
        reason_code="indirect_collection_art_14",
        exempt=False,
        **kw,
    )


def stamp_obligation_evaluation(
    lead: Any,
    decision: ObligationDecision,
    *,
    controller_own_company_id: Optional[str] = None,
    controller_name: Optional[str] = None,
) -> None:
    """Merge assessment evidence onto ``lead.normalized['rodo']`` without clobbering delivery."""
    from sqlalchemy.orm.attributes import flag_modified

    now = datetime.now(timezone.utc).isoformat()
    norm: dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    block: dict[str, Any] = {**_rodo_block(norm)}
    block["obligation"] = decision.to_dict()
    assessment = decision.assessment_evidence(evaluated_at=now)
    oc_id = str(controller_own_company_id or "").strip()
    name = str(controller_name or "").strip()
    if oc_id:
        block["controller_own_company_id"] = oc_id
        assessment["controller_own_company_id"] = oc_id
    if name:
        block["controller_name"] = name
        assessment["controller_name"] = name
    block["assessment"] = assessment
    block["evaluated_at"] = now
    if decision.article:
        block["article"] = decision.article

    current = str(block.get("status") or "").strip().lower()
    if current not in _SATISFIED_STATUSES:
        if decision.state == "exempt":
            block["status"] = "exempt"
            block["exemption_code"] = decision.reason_code
            block["compliance_state"] = "exempt"
        elif decision.state == "review_required":
            block["status"] = "review_required"
            block["compliance_state"] = "review_required"
        elif decision.state == "delivery_required":
            block["status"] = "delivery_required"
            block["compliance_state"] = "delivery_required"
        elif decision.state == "compliant":
            block["compliance_state"] = "compliant"
        else:
            block["compliance_state"] = decision.state
    elif not block.get("compliance_state"):
        block["compliance_state"] = (
            "delivered" if current in ("sent", "satisfied") else ("exempt" if current == "exempt" else "compliant")
        )

    norm["rodo"] = block
    lead.normalized = norm
    flag_modified(lead, "normalized")


__all__ = [
    "Article",
    "AssessmentState",
    "CollectionPath",
    "ComplianceState",
    "ObligationAction",
    "ObligationDecision",
    "classify_collection_path",
    "evaluate_lead_rodo_obligation",
    "notice_provided_at_source",
    "stamp_obligation_evaluation",
]
