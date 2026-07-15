"""ADR-022 policy schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


@dataclass
class MatchPolicy:
    identifier_fields: list[str] = field(default_factory=lambda: ["email", "phone"])
    target_route_intent: str = "sales_inquiry"
    require_entity_profile_match: bool = True
    require_offering_match: bool = False
    allowed_lifecycle_statuses: list[str] = field(
        default_factory=lambda: ["new", "reviewing", "waiting_for_information"]
    )
    window_days: int = 90
    auto_attach_on: str = "strong_single"
    review_on: list[str] = field(default_factory=lambda: ["possible", "conflict", "multiple"])

    @classmethod
    def from_dict(cls, raw: Any) -> MatchPolicy:
        data = _record(raw)
        fields = data.get("identifier_fields")
        lifecycle = data.get("allowed_lifecycle_statuses")
        review_on = data.get("review_on")
        return cls(
            identifier_fields=list(fields) if isinstance(fields, list) else ["email", "phone"],
            target_route_intent=str(data.get("target_route_intent") or "sales_inquiry"),
            require_entity_profile_match=bool(data.get("require_entity_profile_match", True)),
            require_offering_match=bool(data.get("require_offering_match", False)),
            allowed_lifecycle_statuses=list(lifecycle)
            if isinstance(lifecycle, list)
            else ["new", "reviewing", "waiting_for_information"],
            window_days=int(data.get("window_days") or 90),
            auto_attach_on=str(data.get("auto_attach_on") or "strong_single"),
            review_on=list(review_on) if isinstance(review_on, list) else ["possible", "conflict", "multiple"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier_fields": list(self.identifier_fields),
            "target_route_intent": self.target_route_intent,
            "require_entity_profile_match": self.require_entity_profile_match,
            "require_offering_match": self.require_offering_match,
            "allowed_lifecycle_statuses": list(self.allowed_lifecycle_statuses),
            "window_days": self.window_days,
            "auto_attach_on": self.auto_attach_on,
            "review_on": list(self.review_on),
        }


@dataclass
class SubmissionPolicy:
    mode: str = "match_or_create"
    match_policy: Optional[MatchPolicy] = None

    @classmethod
    def from_dict(cls, raw: Any) -> SubmissionPolicy:
        data = _record(raw)
        mode = str(data.get("mode") or "match_or_create").strip()
        match_raw = data.get("match_policy")
        match_policy = MatchPolicy.from_dict(match_raw) if match_raw else None
        return cls(mode=mode, match_policy=match_policy)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"mode": self.mode}
        if self.match_policy is not None:
            out["match_policy"] = self.match_policy.to_dict()
        return out


@dataclass
class EffectivePolicy:
    purpose: str
    target_entity_profile_code: str
    submission_policy: SubmissionPolicy
    form_id: Optional[str] = None
    published_version: int = 0
    publication_id: Optional[str] = None
    invite_id: Optional[str] = None
    application_id: Optional[str] = None
    source: Optional[dict[str, Any]] = None

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "purpose": self.purpose,
            "target_entity_profile_code": self.target_entity_profile_code,
            "submission_policy": self.submission_policy.to_dict(),
            "form_id": self.form_id,
            "published_version": self.published_version,
            "publication_id": self.publication_id,
            "invite_id": self.invite_id,
            "application_id": self.application_id,
            "source": dict(self.source or {}),
        }


@dataclass
class MatchResult:
    confidence: str
    matched_application_ids: list[str] = field(default_factory=list)
    suggested_action: str = "none"
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "matched_application_ids": list(self.matched_application_ids),
            "suggested_action": self.suggested_action,
            "reasons": list(self.reasons),
        }


@dataclass
class SubmitTargetResolution:
    target_lead_id: str
    action: str
    match_result: Optional[MatchResult] = None
    draft_lead_abandoned: bool = False
