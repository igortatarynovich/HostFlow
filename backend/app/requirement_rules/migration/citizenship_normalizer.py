"""Citizenship normalization for ADR-018 historical migration (PR 2B-4.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from backend.app.document_types.registry import normalize_input_doc_type
from backend.app.requirement_rules.migration.iso_country import normalize_country_iso2

CitizenshipStatus = Literal["resolved", "unresolved", "conflict"]

IDENTITY_DOCUMENT_TYPES = frozenset(
    {
        "passport",
        "national_identity_card",
        "national_id",
        "id_card",
        "identity_document",
    }
)

_LEGACY_EXTRA_CITIZENSHIP_KEYS = (
    "citizenship",
    "nationality",
    "obywatelstwo",
    "country_of_citizenship",
    "citizenship_country",
    "nationality_country",
)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


@dataclass(frozen=True)
class CitizenshipSource:
    iso2: str
    source_key: str
    raw_value: str


@dataclass(frozen=True)
class CitizenshipNormalizationResult:
    status: CitizenshipStatus
    iso2: Optional[str]
    provenance: Optional[str]
    sources: tuple[CitizenshipSource, ...]
    conflict_values: tuple[str, ...]

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved" and bool(self.iso2)


def _candidate_extra(candidate: Any) -> dict[str, Any]:
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    return extra if isinstance(extra, dict) else {}


def _candidate_personal(candidate: Any) -> dict[str, Any]:
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    return personal if isinstance(personal, dict) else {}


def _add_source(
    sources: list[CitizenshipSource],
    *,
    raw_value: Any,
    source_key: str,
) -> None:
    iso2 = normalize_country_iso2(raw_value)
    if not iso2:
        return
    sources.append(
        CitizenshipSource(
            iso2=iso2,
            source_key=source_key,
            raw_value=str(raw_value).strip(),
        )
    )


def _identity_doc_nationality(doc: Any) -> Optional[str]:
    stored = _norm(getattr(doc, "doc_type", ""))
    canonical = _norm(normalize_input_doc_type(stored))
    if canonical not in IDENTITY_DOCUMENT_TYPES and stored not in IDENTITY_DOCUMENT_TYPES:
        return None
    status_raw = getattr(doc, "status", None)
    review_status = status_raw.value if hasattr(status_raw, "value") else str(status_raw or "")
    if _norm(review_status) != "approved":
        return None
    meta = getattr(doc, "meta", None) or {}
    if not isinstance(meta, dict):
        return None
    extracted = meta.get("extracted_fields") or meta.get("fields")
    if isinstance(extracted, dict):
        for key in ("nationality", "citizenship", "country_of_citizenship"):
            value = extracted.get(key)
            if value:
                return str(value)
    document_data = meta.get("document_data")
    if isinstance(document_data, dict):
        for key in ("nationality", "citizenship"):
            value = document_data.get(key)
            if value:
                return str(value)
    for key in ("nationality", "citizenship", "country"):
        value = meta.get(key)
        if value:
            return str(value)
    return None


def assess_citizenship(
    candidate: Any,
    *,
    documents: tuple[Any, ...] | list[Any] = (),
) -> CitizenshipNormalizationResult:
    """Collect citizenship from trusted sources; detect conflicts."""
    extra = _candidate_extra(candidate)
    personal = _candidate_personal(candidate)

    sources: list[CitizenshipSource] = []

    canonical = getattr(candidate, "citizenship", None)
    if canonical:
        _add_source(sources, raw_value=canonical, source_key="canonical_citizenship")

    personal_value = personal.get("citizenship")
    if personal_value:
        _add_source(sources, raw_value=personal_value, source_key="structured_personal_data")

    extra_citizenship = extra.get("citizenship")
    if extra_citizenship:
        _add_source(sources, raw_value=extra_citizenship, source_key="canonical_extra_citizenship")

    for key in _LEGACY_EXTRA_CITIZENSHIP_KEYS:
        if key == "citizenship":
            continue
        value = extra.get(key)
        if value:
            _add_source(sources, raw_value=value, source_key=f"extra:{key}")

    for doc in documents:
        nationality = _identity_doc_nationality(doc)
        if nationality:
            _add_source(
                sources,
                raw_value=nationality,
                source_key=f"approved_identity_document:{getattr(doc, 'id', 'unknown')}",
            )

    legacy_form = extra.get("form_fields") or extra.get("intake_fields") or extra.get("meta_form")
    if isinstance(legacy_form, dict):
        for key in ("citizenship", "nationality", "obywatelstwo", "country"):
            value = legacy_form.get(key)
            if value:
                mapped = normalize_country_iso2(value)
                if mapped:
                    _add_source(
                        sources,
                        raw_value=value,
                        source_key=f"legacy_form:{key}",
                    )

    if not sources:
        return CitizenshipNormalizationResult(
            status="unresolved",
            iso2=None,
            provenance=None,
            sources=(),
            conflict_values=(),
        )

    unique_iso2 = {source.iso2 for source in sources}
    if len(unique_iso2) > 1:
        return CitizenshipNormalizationResult(
            status="conflict",
            iso2=None,
            provenance=None,
            sources=tuple(sources),
            conflict_values=tuple(sorted(unique_iso2)),
        )

    # Highest-priority source wins for provenance (first in trust order above).
    winner = sources[0]
    return CitizenshipNormalizationResult(
        status="resolved",
        iso2=winner.iso2,
        provenance=winner.source_key,
        sources=tuple(sources),
        conflict_values=(),
    )


def apply_citizenship_normalization(
    candidate: Any,
    result: CitizenshipNormalizationResult,
    *,
    dry_run: bool,
) -> bool:
    """Persist resolved citizenship with provenance marker. Returns True if changed."""
    if not result.is_resolved:
        return False
    extra = _candidate_extra(candidate)
    current = normalize_country_iso2(extra.get("citizenship"))
    if current == result.iso2 and extra.get("adr018_citizenship_provenance") == result.provenance:
        return False
    if dry_run:
        return True
    extra = dict(extra)
    extra["citizenship"] = result.iso2
    extra["adr018_citizenship_provenance"] = {
        "source": result.provenance,
        "migration": "2B-4.2",
    }
    if hasattr(candidate, "_set_extra"):
        candidate._set_extra(extra)
    else:
        candidate.extra = extra
    return True


__all__ = [
    "CitizenshipNormalizationResult",
    "CitizenshipSource",
    "apply_citizenship_normalization",
    "assess_citizenship",
]
