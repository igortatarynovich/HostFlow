"""Forms Platform C3 — Builder session over FormDefinition ↔ Draft.

No Adapter, no publish, no resolve, no Contract Identity.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from backend.app.forms_platform.builder.composition import FormDraftComposition
from backend.app.forms_platform.builder.definition import FormDefinition
from backend.app.forms_platform.builder.draft_persistence import DraftRecord, InMemoryDraftStore
from backend.app.forms_platform.builder.state import (
    EVENT_BEGIN_SAVE,
    EVENT_CLOSE,
    EVENT_EDIT,
    EVENT_SAVE_CONFLICT,
    EVENT_SAVE_OK,
    EVENT_SAVE_VALIDATION_ERROR,
    STATE_NEW,
    transition,
)
from backend.app.forms_platform.errors import (
    FormsBuilderCompositionInvalidError,
    FormsBuilderDraftConflictError,
)
from backend.app.forms_platform.field_catalog.registry import FieldCatalogRegistry


@dataclass(frozen=True, slots=True)
class BuilderSession:
    """In-memory editor session. Dirty vs Saved are both mutable drafts."""

    tenant_id: str
    definition: FormDefinition
    state: str
    revision: int | None = None
    form_id: str | None = None


def new_session(
    *,
    tenant_id: str,
    composition: FormDraftComposition,
    form_id: str | None = None,
) -> BuilderSession:
    tid = str(tenant_id or "").strip()
    if not tid:
        raise FormsBuilderCompositionInvalidError(details={"reason": "empty_tenant_id"})
    definition = FormDefinition(definition_id=composition.draft_id, composition=composition)
    return BuilderSession(
        tenant_id=tid,
        definition=definition,
        state=STATE_NEW,
        revision=None,
        form_id=str(form_id).strip() if form_id else None,
    )


def edit_session(session: BuilderSession, composition: FormDraftComposition) -> BuilderSession:
    nxt = transition(session.state, EVENT_EDIT)
    definition = session.definition.replace_composition(composition)
    return replace(session, definition=definition, state=nxt)


def begin_save(session: BuilderSession) -> BuilderSession:
    return replace(session, state=transition(session.state, EVENT_BEGIN_SAVE))


def complete_save(session: BuilderSession, record: DraftRecord) -> BuilderSession:
    return replace(
        session,
        state=transition(session.state, EVENT_SAVE_OK),
        revision=int(record.revision),
        form_id=record.form_id,
    )


def fail_save_validation(session: BuilderSession) -> BuilderSession:
    return replace(session, state=transition(session.state, EVENT_SAVE_VALIDATION_ERROR))


def fail_save_conflict(session: BuilderSession) -> BuilderSession:
    return replace(session, state=transition(session.state, EVENT_SAVE_CONFLICT))


def close_session(session: BuilderSession) -> BuilderSession:
    return replace(session, state=transition(session.state, EVENT_CLOSE))


def save_session(
    session: BuilderSession,
    store: InMemoryDraftStore,
    *,
    registry: FieldCatalogRegistry | None = None,
    require_valid: bool = True,
) -> BuilderSession:
    """Persist Draft only. Must never publish or touch publication identity."""
    working = begin_save(session)
    composition = working.definition.composition
    try:
        if working.revision is None:
            record = store.create(
                tenant_id=working.tenant_id,
                composition=composition,
                form_id=working.form_id,
                registry=registry,
                require_valid=require_valid,
            )
        else:
            record = store.update(
                tenant_id=working.tenant_id,
                draft_id=working.definition.definition_id,
                composition=composition,
                expected_revision=working.revision,
                registry=registry,
                require_valid=require_valid,
            )
    except FormsBuilderCompositionInvalidError:
        fail_save_validation(working)
        raise
    except FormsBuilderDraftConflictError:
        fail_save_conflict(working)
        raise
    return complete_save(working, record)
