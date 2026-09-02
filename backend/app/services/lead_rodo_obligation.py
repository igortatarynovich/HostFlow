"""Lead RODO information-obligation evaluation (GDPR art.13 / art.14).

Platform-mandatory: a tenant cannot disable evaluation or fulfillment.
The engine decides *whether* outbound delivery is required. HostFlow is
delivery infrastructure; the operating firm (OwnCompany) remains the
controller named in the notice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping, Optional

CollectionPath = Literal["direct", "indirect"]
Article = Literal["13", "14"]
ObligationAction = Literal[
    "no_delivery_source_provided",
    "no_delivery_already_notified",
    "no_delivery_exempt",
    "delivery_required",
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
_NEGATIVE_STATUSES = frozenset({"failed", "deferred", "undelivered", "pending_channel", "pending_policy"})


@dataclass(frozen=True, slots=True)
class ObligationDecision:
    action: ObligationAction
    article: Optional[Article]
    collection_path: CollectionPath
    reason_code: str
    notice_at_source: bool
    already_notified: bool
    exempt: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "article": self.article,
            "collection_path": self.collection_path,
            "reason_code": self.reason_code,
            "notice_at_source": self.notice_at_source,
            "already_notified": self.already_notified,
            "exempt": self.exempt,
        }


def classify_collection_path(source: str) -> CollectionPath:
    s = str(source or "").strip().lower()
    if not s:
        return "indirect"
    if s in _DIRECT_SOURCES or s.startswith("telegram") or s.startswith("public"):
        return "direct"
    if s in _INDIRECT_SOURCES or "import" in s:
        return "indirect"
    return "indirect"


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
    if str(block.get("status") or "").strip().lower() == "exempt":
        code = str(block.get("exemption_code") or "art_14_5_a").strip().lower()
        return code or "art_14_5_a"
    raw = block.get("exemption_code") or (normalized or {}).get("rodo_exempt_code")
    code = str(raw or "").strip().lower()
    if code in _EXEMPT_CODES:
        return code
    flag = (normalized or {}).get("rodo_exempt") if isinstance(normalized, Mapping) else None
    if flag is True or (isinstance(flag, str) and flag.strip().lower() in ("true", "1", "yes")):
        return "art_14_5_a"
    return None


def evaluate_lead_rodo_obligation(
    *,
    source: str,
    normalized: Optional[Mapping[str, Any]] = None,
) -> ObligationDecision:
    """Decide the information obligation for a recorded lead.

    Does not send mail. Callers persist the decision and, when
    ``action == delivery_required``, run outbound fulfillment.
    """
    path = classify_collection_path(source)
    article: Article = "13" if path == "direct" else "14"
    notice = notice_provided_at_source(normalized)
    block = _rodo_block(normalized)
    exempt_code = _exemption_code(normalized, block)
    already = _already_notified(block)
    source_status = str(block.get("status") or "").strip().lower() == "source_provided"

    if exempt_code:
        return ObligationDecision(
            action="no_delivery_exempt",
            article=article,
            collection_path=path,
            reason_code=exempt_code,
            notice_at_source=notice,
            already_notified=already,
            exempt=True,
        )
    if already:
        return ObligationDecision(
            action="no_delivery_already_notified",
            article=article,
            collection_path=path,
            reason_code="already_notified",
            notice_at_source=notice,
            already_notified=True,
            exempt=False,
        )
    if notice or source_status:
        return ObligationDecision(
            action="no_delivery_source_provided",
            article="13" if path == "direct" or notice else article,
            collection_path=path,
            reason_code="notice_at_source" if notice else "source_provided",
            notice_at_source=notice or source_status,
            already_notified=False,
            exempt=False,
        )
    if path == "direct":
        return ObligationDecision(
            action="delivery_required",
            article="13",
            collection_path="direct",
            reason_code="direct_collection_notice_unproven",
            notice_at_source=False,
            already_notified=False,
            exempt=False,
        )
    return ObligationDecision(
        action="delivery_required",
        article="14",
        collection_path="indirect",
        reason_code="indirect_collection_art_14",
        notice_at_source=False,
        already_notified=False,
        exempt=False,
    )


def stamp_obligation_evaluation(
    lead: Any,
    decision: ObligationDecision,
    *,
    controller_own_company_id: Optional[str] = None,
    controller_name: Optional[str] = None,
) -> None:
    """Merge the evaluation onto ``lead.normalized['rodo']`` without clobbering delivery status."""
    from sqlalchemy.orm.attributes import flag_modified

    now = datetime.now(timezone.utc).isoformat()
    norm: dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    block: dict[str, Any] = {**_rodo_block(norm)}
    block["obligation"] = decision.to_dict()
    block["evaluated_at"] = now
    if decision.article:
        block["article"] = decision.article
    oc_id = str(controller_own_company_id or "").strip()
    if oc_id:
        block["controller_own_company_id"] = oc_id
    name = str(controller_name or "").strip()
    if name:
        block["controller_name"] = name
    if decision.action == "no_delivery_exempt" and str(block.get("status") or "") not in _SATISFIED_STATUSES:
        block["status"] = "exempt"
        block["exemption_code"] = decision.reason_code
    norm["rodo"] = block
    lead.normalized = norm
    flag_modified(lead, "normalized")


__all__ = [
    "Article",
    "CollectionPath",
    "ObligationAction",
    "ObligationDecision",
    "classify_collection_path",
    "evaluate_lead_rodo_obligation",
    "notice_provided_at_source",
    "stamp_obligation_evaluation",
]
