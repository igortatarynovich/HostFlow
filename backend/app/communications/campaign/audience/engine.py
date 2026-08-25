"""C2.3 PR-2 — Pure Audience Resolver engine.

Public ops: resolve · dry_run · diagnostics.
Transforms AudienceDefinition → snapshot candidates.
No SQL, ORM, Sender, Thread, Intent execute, or module imports.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.app.communications.automation.evaluator.conditions import (
    ConditionError,
    evaluate_condition,
)
from backend.app.communications.campaign.audience.types import (
    DEFINITION_TYPE_FILTER,
    DEFINITION_TYPE_STATIC_LIST,
    DEFINITION_TYPES,
    DIAG_DUPLICATE_RECIPIENT,
    DIAG_EMPTY_AUDIENCE,
    DIAG_ENTITY_POOL_REQUIRED,
    DIAG_ENTITY_SKIPPED,
    DIAG_FILTER_INVALID,
    DIAG_INVALID_DEFINITION,
    DIAG_INVALID_RECIPIENT,
    DIAG_UNKNOWN_DEFINITION_TYPE,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    AudienceDefinitionPayload,
    Diagnostic,
    EntityCandidate,
    ResolveContext,
    ResolvedRecipient,
    ResolveResult,
    SkippedCandidate,
)


def _diag(
    code: str,
    message: str,
    *,
    severity: str = SEVERITY_ERROR,
    path: str | None = None,
    details: dict[str, Any] | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        path=path,
        details=details or {},
    )


def _fingerprint(definition: AudienceDefinitionPayload) -> dict[str, Any]:
    return {
        "version_id": definition.version_id,
        "definition_type": str(definition.definition_type or "").strip().lower(),
        "definition_keys": sorted(str(k) for k in (definition.definition or {}).keys()),
    }


def _norm_address(raw: Any) -> str | None:
    addr = str(raw or "").strip()
    return addr or None


def _recipient_key(entity_type: str, entity_id: str, address: str) -> tuple[str, str, str]:
    return (entity_type, entity_id, address.lower())


def _parse_static_row(
    raw: Any,
    *,
    path: str,
) -> tuple[ResolvedRecipient | None, SkippedCandidate | None, list[Diagnostic]]:
    diags: list[Diagnostic] = []
    if not isinstance(raw, Mapping):
        diags.append(
            _diag(
                DIAG_INVALID_RECIPIENT,
                "static_list item must be an object",
                path=path,
            )
        )
        return None, None, diags

    entity_type = str(raw.get("entity_type") or "").strip()
    entity_id = str(raw.get("entity_id") or "").strip()
    address = _norm_address(raw.get("address"))
    label = str(raw["label"]).strip() if raw.get("label") is not None else None
    snapshot = raw.get("snapshot")
    snap = dict(snapshot) if isinstance(snapshot, Mapping) else {}

    if not address:
        skipped = SkippedCandidate(
            entity_type=entity_type,
            entity_id=entity_id,
            address=None,
            reason_codes=(DIAG_INVALID_RECIPIENT, "address_required"),
            message="Recipient missing address",
        )
        diags.append(
            _diag(
                DIAG_ENTITY_SKIPPED,
                "Skipped recipient without address",
                severity=SEVERITY_WARNING,
                path=path,
                details={"entity_type": entity_type, "entity_id": entity_id},
            )
        )
        return None, skipped, diags

    return (
        ResolvedRecipient(
            entity_type=entity_type,
            entity_id=entity_id,
            address=address,
            label=label,
            snapshot=snap,
        ),
        None,
        diags,
    )


def _resolve_static_list(
    definition: AudienceDefinitionPayload,
    *,
    diags: list[Diagnostic],
) -> tuple[list[ResolvedRecipient], list[SkippedCandidate]]:
    body = definition.definition or {}
    raw_list = body.get("recipients")
    if raw_list is None:
        raw_list = body.get("items")
    if raw_list is None:
        diags.append(
            _diag(
                DIAG_INVALID_DEFINITION,
                "static_list requires definition.recipients (or items)",
                path="$.recipients",
            )
        )
        return [], []
    if not isinstance(raw_list, (list, tuple)):
        diags.append(
            _diag(
                DIAG_INVALID_DEFINITION,
                "definition.recipients must be a list",
                path="$.recipients",
            )
        )
        return [], []

    recipients: list[ResolvedRecipient] = []
    skipped: list[SkippedCandidate] = []
    seen: set[tuple[str, str, str]] = set()

    for i, raw in enumerate(raw_list):
        path = f"$.recipients[{i}]"
        recipient, skip, row_diags = _parse_static_row(raw, path=path)
        diags.extend(row_diags)
        if skip is not None:
            skipped.append(skip)
            continue
        if recipient is None:
            continue
        key = _recipient_key(recipient.entity_type, recipient.entity_id, recipient.address)
        if key in seen:
            skipped.append(
                SkippedCandidate(
                    entity_type=recipient.entity_type,
                    entity_id=recipient.entity_id,
                    address=recipient.address,
                    reason_codes=(DIAG_DUPLICATE_RECIPIENT,),
                    message="Duplicate recipient in definition",
                )
            )
            diags.append(
                _diag(
                    DIAG_DUPLICATE_RECIPIENT,
                    "Duplicate recipient skipped",
                    severity=SEVERITY_WARNING,
                    path=path,
                    details={"address": recipient.address},
                )
            )
            continue
        seen.add(key)
        recipients.append(recipient)

    return recipients, skipped


def _entity_match_data(entity: EntityCandidate) -> dict[str, Any]:
    data = dict(entity.attributes or {})
    # Convenience roots for filter paths.
    data.setdefault("entity_type", entity.entity_type)
    data.setdefault("entity_id", entity.entity_id)
    data.setdefault("address", entity.address)
    data.setdefault("label", entity.label)
    return data


def _resolve_filter(
    definition: AudienceDefinitionPayload,
    context: ResolveContext,
    *,
    diags: list[Diagnostic],
) -> tuple[list[ResolvedRecipient], list[SkippedCandidate]]:
    body = definition.definition or {}
    filt = body.get("filter")
    if filt is None:
        filt = body.get("conditions")
    if filt is None:
        filt = {}
    if not isinstance(filt, Mapping):
        diags.append(
            _diag(
                DIAG_FILTER_INVALID,
                "filter/conditions must be an object",
                path="$.filter",
            )
        )
        return [], []

    entities = list(context.entities or ())
    # Explicit empty pool is allowed (→ empty audience); missing key vs empty:
    # ResolveContext always has entities (default tuple). Pool required only when
    # caller forgot to supply and definition expects live selection — we treat
    # empty as valid empty snapshot, but flag when filter references pool and
    # extras say require_pool.
    if bool((context.extras or {}).get("require_entity_pool")) and not entities:
        diags.append(
            _diag(
                DIAG_ENTITY_POOL_REQUIRED,
                "filter resolution requires a non-empty entity pool",
                path="$.entities",
            )
        )
        return [], []

    recipients: list[ResolvedRecipient] = []
    skipped: list[SkippedCandidate] = []
    seen: set[tuple[str, str, str]] = set()

    for idx, entity in enumerate(entities):
        path = f"$.entities[{idx}]"
        try:
            matched = evaluate_condition(filt, _entity_match_data(entity))
        except ConditionError as exc:
            diags.append(
                _diag(
                    DIAG_FILTER_INVALID,
                    exc.message,
                    path=exc.path or path,
                )
            )
            return [], []

        if not matched:
            continue

        address = _norm_address(entity.address)
        if not address:
            skipped.append(
                SkippedCandidate(
                    entity_type=str(entity.entity_type or ""),
                    entity_id=str(entity.entity_id or ""),
                    address=None,
                    reason_codes=(DIAG_INVALID_RECIPIENT, "address_required"),
                    message="Matched entity missing address",
                )
            )
            diags.append(
                _diag(
                    DIAG_ENTITY_SKIPPED,
                    "Matched entity skipped — no address",
                    severity=SEVERITY_WARNING,
                    path=path,
                    details={
                        "entity_type": entity.entity_type,
                        "entity_id": entity.entity_id,
                    },
                )
            )
            continue

        entity_type = str(entity.entity_type or "").strip()
        entity_id = str(entity.entity_id or "").strip()
        key = _recipient_key(entity_type, entity_id, address)
        if key in seen:
            skipped.append(
                SkippedCandidate(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    address=address,
                    reason_codes=(DIAG_DUPLICATE_RECIPIENT,),
                    message="Duplicate entity in pool",
                )
            )
            continue
        seen.add(key)

        snap = dict(entity.attributes or {})
        recipients.append(
            ResolvedRecipient(
                entity_type=entity_type,
                entity_id=entity_id,
                address=address,
                label=(str(entity.label).strip() if entity.label else None),
                snapshot=snap,
            )
        )

    return recipients, skipped


def resolve(
    definition: AudienceDefinitionPayload,
    context: ResolveContext | None = None,
) -> ResolveResult:
    """Resolve an audience definition into a frozen snapshot candidate list.

    Deterministic: same inputs → identical ResolveResult.
    Does not persist Run/Recipient, create Intent, send, or touch Thread.
    """
    ctx = context or ResolveContext()
    diags: list[Diagnostic] = []
    dtype = str(definition.definition_type or "").strip().lower()
    fp = _fingerprint(definition)

    if dtype not in DEFINITION_TYPES:
        diags.append(
            _diag(
                DIAG_UNKNOWN_DEFINITION_TYPE,
                f"Unknown audience definition_type: {definition.definition_type!r}",
                path="$.definition_type",
                details={"allowed": sorted(DEFINITION_TYPES)},
            )
        )
        return ResolveResult(
            ok=False,
            definition_type=dtype,
            recipients=(),
            skipped=(),
            diagnostics=tuple(diags),
            fingerprint=fp,
        )

    if not isinstance(definition.definition, Mapping):
        diags.append(
            _diag(
                DIAG_INVALID_DEFINITION,
                "definition must be an object",
                path="$.definition",
            )
        )
        return ResolveResult(
            ok=False,
            definition_type=dtype,
            recipients=(),
            skipped=(),
            diagnostics=tuple(diags),
            fingerprint=fp,
        )

    if dtype == DEFINITION_TYPE_STATIC_LIST:
        recipients, skipped = _resolve_static_list(definition, diags=diags)
    else:
        recipients, skipped = _resolve_filter(definition, ctx, diags=diags)

    # Hard errors (severity=error) mark ok=False; warnings alone do not.
    hard = [d for d in diags if d.severity == SEVERITY_ERROR]
    if hard:
        return ResolveResult(
            ok=False,
            definition_type=dtype,
            recipients=(),
            skipped=tuple(skipped),
            diagnostics=tuple(diags),
            fingerprint=fp,
        )

    # Stable order for reproducibility.
    recipients_sorted = tuple(
        sorted(
            recipients,
            key=lambda r: (r.entity_type, r.entity_id, r.address.lower()),
        )
    )

    if not recipients_sorted:
        diags.append(
            _diag(
                DIAG_EMPTY_AUDIENCE,
                "Audience resolved to zero recipients",
                severity=SEVERITY_INFO,
            )
        )

    return ResolveResult(
        ok=True,
        definition_type=dtype,
        recipients=recipients_sorted,
        skipped=tuple(skipped),
        diagnostics=tuple(diags),
        fingerprint=fp,
    )


def dry_run(
    definition: AudienceDefinitionPayload,
    context: ResolveContext | None = None,
) -> ResolveResult:
    """Alias of resolve — no side effects either way."""
    return resolve(definition, context)


def diagnostics(
    definition: AudienceDefinitionPayload,
    context: ResolveContext | None = None,
) -> tuple[Diagnostic, ...]:
    """Return diagnostics only (still runs full resolve for consistency)."""
    return resolve(definition, context).diagnostics


__all__ = ["resolve", "dry_run", "diagnostics"]
