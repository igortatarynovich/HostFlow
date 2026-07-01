"""P1.14 — Surface candidate audit record (day_surface_candidate_audit_v1).

Captures what the surface selection pipeline chose, why, and default exposure/reaction/
learning statuses for later P1.15 linkage. No UI, API, memory, or learning mutation.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping, Sequence
from uuid import uuid4

RECORD_VERSION = "day_surface_candidate_audit_v1"

SelectedSource = Literal["deterministic", "llm_refined", "blocked"]
UiExposureStatus = Literal["not_exposed"]
ReactionStatus = Literal["pending"]
LearningStatus = Literal["not_processed"]

DEFAULT_UI_EXPOSURE_STATUS: UiExposureStatus = "not_exposed"
DEFAULT_REACTION_STATUS: ReactionStatus = "pending"
DEFAULT_LEARNING_STATUS: LearningStatus = "not_processed"

AUDIT_RECORD_KEYS: tuple[str, ...] = (
    "record_version",
    "audit_id",
    "surface",
    "candidate_id",
    "selected_source",
    "display_text_hash",
    "display_text_snapshot",
    "selection_reason",
    "used_llm",
    "dataset_candidate",
    "quality_score",
    "confidence",
    "degraded",
    "render_trace",
    "llm_trace",
    "created_at",
    "ui_exposure_status",
    "reaction_status",
    "learning_status",
)

_RENDER_TRACE_KEYS = ("package_ref", "evaluation_ref", "render_ref")
_LLM_TRACE_KEYS = ("generation_ref", "prompt_ref", "response_ref")

_FORBIDDEN_PROFILE_KEYS = frozenset(
    {
        "user_profile",
        "profile",
        "personal_data",
        "contacts",
        "email",
        "phone",
        "first_name",
        "last_name",
        "full_name",
        "address",
        "birth_date",
        "passport",
        "national_id",
    }
)

_CANDIDATE_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class DaySurfaceCandidateAuditValidationError(ValueError):
    """Raised when an audit record fails P1.14 invariants."""


@dataclass(frozen=True, slots=True)
class SurfaceCandidateRenderTrace:
    package_ref: str
    evaluation_ref: str
    render_ref: str

    def to_dict(self) -> dict[str, str]:
        return {
            "package_ref": str(self.package_ref).strip(),
            "evaluation_ref": str(self.evaluation_ref).strip(),
            "render_ref": str(self.render_ref).strip(),
        }


@dataclass(frozen=True, slots=True)
class SurfaceCandidateLlmTrace:
    generation_ref: str
    prompt_ref: str
    response_ref: str

    def to_dict(self) -> dict[str, str]:
        return {
            "generation_ref": str(self.generation_ref).strip(),
            "prompt_ref": str(self.prompt_ref).strip(),
            "response_ref": str(self.response_ref).strip(),
        }


@dataclass(frozen=True, slots=True)
class SurfaceCandidateSelectionV1:
    """Minimal selected-candidate artifact from P1.13 consumed by P1.14."""

    surface: str
    candidate_id: str
    selected_source: SelectedSource
    selection_reason: str
    display_text: str | None = None
    display_text_snapshot: str | None = None
    dataset_candidate: bool = False
    quality_score: float | None = None
    confidence: float | None = None
    degraded: bool = False
    render_trace: SurfaceCandidateRenderTrace | None = None
    llm_trace: SurfaceCandidateLlmTrace | None = None
    created_at: datetime | None = None
    audit_id: str | None = None


def normalize_display_text_for_hash(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").strip()


def hash_display_text(text: str) -> str:
    normalized = normalize_display_text_for_hash(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_trace(
    trace: SurfaceCandidateRenderTrace | SurfaceCandidateLlmTrace | Mapping[str, Any] | None,
    allowed_keys: Sequence[str],
) -> dict[str, str] | None:
    if trace is None:
        return None
    if hasattr(trace, "to_dict"):
        raw = trace.to_dict()  # type: ignore[union-attr]
    else:
        raw = dict(trace)
    out: dict[str, str] = {}
    for key in allowed_keys:
        val = raw.get(key)
        if val is None:
            continue
        s = str(val).strip()
        if s:
            out[key] = s
    return out or None


def _used_llm_for_source(selected_source: SelectedSource) -> bool:
    return selected_source == "llm_refined"


def _display_text_hash_for_selection(selection: SurfaceCandidateSelectionV1) -> str | None:
    if selection.selected_source == "blocked":
        return None
    if selection.display_text is not None and str(selection.display_text).strip():
        return hash_display_text(selection.display_text)
    return None


def _snapshot_for_selection(selection: SurfaceCandidateSelectionV1) -> str | None:
    if selection.selected_source == "blocked":
        return None
    snap = selection.display_text_snapshot
    if snap is not None and str(snap).strip():
        return str(snap)
    if selection.display_text is not None and str(selection.display_text).strip():
        return str(selection.display_text)
    return None


def build_day_surface_candidate_audit_v1(
    selection: SurfaceCandidateSelectionV1,
) -> dict[str, Any]:
    """Build a normalized audit artifact for a P1.13 selected candidate."""
    errors = validate_surface_candidate_selection_v1(selection)
    if errors:
        raise DaySurfaceCandidateAuditValidationError("; ".join(errors))

    created_at = selection.created_at or _utc_now()
    record: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "audit_id": str(selection.audit_id or uuid4()),
        "surface": str(selection.surface).strip(),
        "candidate_id": str(selection.candidate_id).strip(),
        "selected_source": selection.selected_source,
        "display_text_hash": _display_text_hash_for_selection(selection),
        "display_text_snapshot": _snapshot_for_selection(selection),
        "selection_reason": str(selection.selection_reason).strip(),
        "used_llm": _used_llm_for_source(selection.selected_source),
        "dataset_candidate": bool(selection.dataset_candidate),
        "quality_score": selection.quality_score,
        "confidence": selection.confidence,
        "degraded": bool(selection.degraded),
        "render_trace": _normalize_trace(selection.render_trace, _RENDER_TRACE_KEYS),
        "llm_trace": _normalize_trace(selection.llm_trace, _LLM_TRACE_KEYS),
        "created_at": _iso_utc(created_at),
        "ui_exposure_status": DEFAULT_UI_EXPOSURE_STATUS,
        "reaction_status": DEFAULT_REACTION_STATUS,
        "learning_status": DEFAULT_LEARNING_STATUS,
    }
    assert_valid_day_surface_candidate_audit_v1(record)
    return record


def validate_surface_candidate_selection_v1(selection: SurfaceCandidateSelectionV1) -> list[str]:
    errors: list[str] = []
    if not str(selection.surface or "").strip():
        errors.append("surface is required")
    candidate_id = str(selection.candidate_id or "").strip()
    if not candidate_id:
        errors.append("candidate_id is required")
    elif not _CANDIDATE_ID_RE.match(candidate_id):
        errors.append("candidate_id must be a UUID")
    if selection.selected_source not in ("deterministic", "llm_refined", "blocked"):
        errors.append("selected_source must be deterministic, llm_refined, or blocked")
    if not str(selection.selection_reason or "").strip():
        errors.append("selection_reason is required")
    errors.extend(_scan_forbidden_profile_keys(selection))
    return errors


def _scan_forbidden_profile_keys(selection: SurfaceCandidateSelectionV1) -> list[str]:
    errors: list[str] = []
    for label, payload in (
        ("render_trace", selection.render_trace),
        ("llm_trace", selection.llm_trace),
    ):
        if payload is None:
            continue
        raw = payload.to_dict() if hasattr(payload, "to_dict") else dict(payload)  # type: ignore[arg-type]
        for key in raw:
            if str(key).strip().lower() in _FORBIDDEN_PROFILE_KEYS:
                errors.append(f"{label} must not contain raw profile key {key!r}")
    return errors


def assert_valid_day_surface_candidate_audit_v1(record: Mapping[str, Any]) -> None:
    errors = validate_day_surface_candidate_audit_v1(record)
    if errors:
        raise DaySurfaceCandidateAuditValidationError("; ".join(errors))


def validate_day_surface_candidate_audit_v1(record: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = [key for key in AUDIT_RECORD_KEYS if key not in record]
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
        return errors

    extra = [key for key in record if key not in AUDIT_RECORD_KEYS]
    if extra:
        errors.append(f"unexpected keys: {', '.join(extra)}")

    if record.get("record_version") != RECORD_VERSION:
        errors.append("record_version must be day_surface_candidate_audit_v1")

    candidate_id = str(record.get("candidate_id") or "").strip()
    if not candidate_id:
        errors.append("candidate_id is required")
    elif not _CANDIDATE_ID_RE.match(candidate_id):
        errors.append("candidate_id must be a UUID")

    selected_source = record.get("selected_source")
    used_llm = record.get("used_llm")
    if selected_source == "deterministic" and used_llm is not False:
        errors.append("deterministic selection requires used_llm=false")
    if selected_source == "llm_refined" and used_llm is not True:
        errors.append("llm_refined selection requires used_llm=true")
    if selected_source == "blocked" and record.get("display_text_hash") is not None:
        errors.append("blocked selection requires display_text_hash=null")

    if record.get("ui_exposure_status") != DEFAULT_UI_EXPOSURE_STATUS:
        errors.append("ui_exposure_status must default to not_exposed")
    if record.get("reaction_status") != DEFAULT_REACTION_STATUS:
        errors.append("reaction_status must default to pending")
    if record.get("learning_status") != DEFAULT_LEARNING_STATUS:
        errors.append("learning_status must default to not_processed")

    errors.extend(_validate_trace_block("render_trace", record.get("render_trace"), _RENDER_TRACE_KEYS))
    errors.extend(_validate_trace_block("llm_trace", record.get("llm_trace"), _LLM_TRACE_KEYS))
    errors.extend(_scan_forbidden_profile_keys_in_record(record))
    return errors


def _validate_trace_block(name: str, block: Any, allowed_keys: Sequence[str]) -> list[str]:
    if block is None:
        return []
    if not isinstance(block, dict):
        return [f"{name} must be an object or null"]
    errors: list[str] = []
    for key in block:
        if key not in allowed_keys:
            errors.append(f"{name} contains unexpected key {key!r}")
        if str(key).strip().lower() in _FORBIDDEN_PROFILE_KEYS:
            errors.append(f"{name} must not contain raw profile key {key!r}")
    for key in allowed_keys:
        val = block.get(key)
        if val is None:
            continue
        if not str(val).strip():
            errors.append(f"{name}.{key} must be non-empty when present")
    return errors


def _scan_forbidden_profile_keys_in_record(record: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in record:
        if str(key).strip().lower() in _FORBIDDEN_PROFILE_KEYS:
            errors.append(f"audit record must not contain raw profile key {key!r}")
    return errors
