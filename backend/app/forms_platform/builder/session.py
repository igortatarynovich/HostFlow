"""Forms Platform C3 — Builder session over FormDefinition ↔ Draft.

No Adapter, no publish, no resolve, no Contract Identity.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from backend.app.forms_platform.builder.composition import FormDraftComposition
from backend.app.forms_platform.builder.definition import FormDefinition
from backend.app.forms_platform.builder.draft_persistence import DraftRecord
from backend.app.forms_platform.builder.state import (
    EVENT_BEGIN_SAVE,
    EVENT_CLOSE,
    EVENT_EDIT,
    EVENT_SAVE_CONFLICT,
    EVENT_SAVE_OK,
    EVENT_SAVE_VALIDATION_ERROR,
    STATE_CLOSED,
    STATE_NEW,
    STATE_SAVED,
    transition,
)
from backend.app.forms_platform.errors import (
    FormsAdapterError,
    FormsBuilderCompositionInvalidError,
    FormsBuilderDraftConflictError,
)
from backend.app.forms_platform.field_catalog.registry import FieldCatalogRegistry


class DraftTipStore(Protocol):
    """Sync draft tip. Not a publication ledger."""

    def create(
        self,
        *,
        tenant_id: str,
        composition: FormDraftComposition,
        form_id: str | None = None,
        registry: FieldCatalogRegistry | None = None,
        require_valid: bool = True,
    ) -> DraftRecord: ...

    def update(
        self,
        *,
        tenant_id: str,
        draft_id: str,
        composition: FormDraftComposition,
        expected_revision: int,
        registry: FieldCatalogRegistry | None = None,
        require_valid: bool = True,
    ) -> DraftRecord: ...


class AsyncDraftTipStore(Protocol):
    """Durable draft tip (SQLAlchemy). Still not Adapter publish."""

    async def create(
        self,
        *,
        tenant_id: str,
        composition: FormDraftComposition,
        form_id: str | None = None,
        registry: FieldCatalogRegistry | None = None,
        require_valid: bool = True,
    ) -> DraftRecord: ...

    async def update(
        self,
        *,
        tenant_id: str,
        draft_id: str,
        composition: FormDraftComposition,
        expected_revision: int,
        registry: FieldCatalogRegistry | None = None,
        require_valid: bool = True,
    ) -> DraftRecord: ...


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


def session_from_error(exc: BaseException) -> BuilderSession | None:
    """Failed save attaches the post-transition session; callers must not ignore it."""
    attached = getattr(exc, "builder_session", None)
    return attached if isinstance(attached, BuilderSession) else None


def _attach_failed_session(exc: FormsAdapterError, session: BuilderSession) -> None:
    exc.builder_session = session
    details = dict(exc.details or {})
    details["builder_state"] = session.state
    exc.details = details


def session_from_record(*, tenant_id: str, record: DraftRecord) -> BuilderSession:
    """Rehydrate a session from a Saved or archived Draft. Not a publication."""
    composition = record.composition_model()
    definition = FormDefinition(definition_id=record.draft_id, composition=composition)
    archived = str(record.status) == "archived"
    return BuilderSession(
        tenant_id=str(tenant_id).strip(),
        definition=definition,
        state=STATE_CLOSED if archived else STATE_SAVED,
        revision=None if archived else int(record.revision),
        form_id=record.form_id,
    )


def save_session(
    session: BuilderSession,
    store: DraftTipStore,
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
    except FormsBuilderCompositionInvalidError as exc:
        _attach_failed_session(exc, fail_save_validation(working))
        raise
    except FormsBuilderDraftConflictError as exc:
        _attach_failed_session(exc, fail_save_conflict(working))
        raise
    return complete_save(working, record)


async def save_session_async(
    session: BuilderSession,
    store: AsyncDraftTipStore,
    *,
    registry: FieldCatalogRegistry | None = None,
    require_valid: bool = True,
) -> BuilderSession:
    """Same as save_session over a durable draft store. Still not publish."""
    working = begin_save(session)
    composition = working.definition.composition
    try:
        if working.revision is None:
            record = await store.create(
                tenant_id=working.tenant_id,
                composition=composition,
                form_id=working.form_id,
                registry=registry,
                require_valid=require_valid,
            )
        else:
            record = await store.update(
                tenant_id=working.tenant_id,
                draft_id=working.definition.definition_id,
                composition=composition,
                expected_revision=working.revision,
                registry=registry,
                require_valid=require_valid,
            )
    except FormsBuilderCompositionInvalidError as exc:
        _attach_failed_session(exc, fail_save_validation(working))
        raise
    except FormsBuilderDraftConflictError as exc:
        _attach_failed_session(exc, fail_save_conflict(working))
        raise
    return complete_save(working, record)
