"""Forms Product Layer P2.4 — Draft Persistence.

Contract id: forms.builder.draft_persistence.v1

Persists only Builder composition drafts (tenant-scoped) with optimistic
revision pins. No publish side effects, no Catalog SoT, no intake mapping,
no UI state.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.forms_platform.builder.composition import (
    BUILDER_COMPOSITION_CONTRACT,
    FormDraftComposition,
    parse_composition,
)
from backend.app.forms_platform.errors import (
    FormsBuilderDraftArchivedError,
    FormsBuilderDraftConflictError,
    FormsBuilderDraftNotFoundError,
    FormsBuilderCompositionInvalidError,
)
from backend.app.forms_platform.field_catalog.registry import FieldCatalogRegistry
from backend.app.models.form_builder_draft import (
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
    FormBuilderDraft,
    FormBuilderDraftRevision,
)
from backend.app.models.mixins import now_utc

BUILDER_DRAFT_PERSISTENCE_CONTRACT = "forms.builder.draft_persistence.v1"


@dataclass(frozen=True, slots=True)
class DraftRecord:
    """Persisted draft tip — composition payload is a frozen composition.v1 dict."""

    tenant_id: str
    draft_id: str
    revision: int
    status: str
    composition: dict[str, Any]
    composition_contract: str = BUILDER_COMPOSITION_CONTRACT
    form_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": BUILDER_DRAFT_PERSISTENCE_CONTRACT,
            "tenant_id": self.tenant_id,
            "draft_id": self.draft_id,
            "revision": self.revision,
            "status": self.status,
            "form_id": self.form_id,
            "composition_contract": self.composition_contract,
            "composition": copy.deepcopy(self.composition),
        }

    def composition_model(self) -> FormDraftComposition:
        return parse_composition(self.composition)


def _serialize_composition(
    composition: FormDraftComposition,
    *,
    registry: FieldCatalogRegistry | None = None,
    require_valid: bool = True,
) -> dict[str, Any]:
    if composition.contract != BUILDER_COMPOSITION_CONTRACT:
        raise FormsBuilderCompositionInvalidError(
            details={
                "reason": "unsupported_composition_contract",
                "contract": composition.contract,
            },
        )
    if require_valid:
        composition.assert_valid(registry)
    # Store exact composition contract payload without transformation.
    return copy.deepcopy(composition.to_dict())


def _record_from_row(row: FormBuilderDraft) -> DraftRecord:
    return DraftRecord(
        tenant_id=str(row.tenant_id),
        draft_id=str(row.draft_id),
        revision=int(row.revision),
        status=str(row.status),
        form_id=str(row.form_id) if row.form_id else None,
        composition_contract=str(row.composition_contract),
        composition=copy.deepcopy(dict(row.composition or {})),
    )


class InMemoryDraftStore:
    """Tenant-isolated in-memory draft store (tests / local clients)."""

    def __init__(self) -> None:
        # (tenant_id, draft_id) → tip
        self._tips: dict[tuple[str, str], DraftRecord] = {}
        # (tenant_id, draft_id, revision) → frozen composition
        self._revisions: dict[tuple[str, str, int], dict[str, Any]] = {}

    def create(
        self,
        *,
        tenant_id: str,
        composition: FormDraftComposition,
        form_id: str | None = None,
        registry: FieldCatalogRegistry | None = None,
        require_valid: bool = True,
    ) -> DraftRecord:
        tid = str(tenant_id or "").strip()
        if not tid:
            raise FormsBuilderCompositionInvalidError(details={"reason": "empty_tenant_id"})
        key = (tid, composition.draft_id)
        if key in self._tips:
            raise FormsBuilderDraftConflictError(
                details={"reason": "draft_already_exists", "draft_id": composition.draft_id},
            )
        payload = _serialize_composition(
            composition, registry=registry, require_valid=require_valid
        )
        record = DraftRecord(
            tenant_id=tid,
            draft_id=composition.draft_id,
            revision=1,
            status=STATUS_ACTIVE,
            form_id=str(form_id).strip() if form_id else None,
            composition_contract=BUILDER_COMPOSITION_CONTRACT,
            composition=payload,
        )
        self._tips[key] = record
        self._revisions[(tid, composition.draft_id, 1)] = copy.deepcopy(payload)
        return record

    def get(self, *, tenant_id: str, draft_id: str) -> DraftRecord:
        key = (str(tenant_id).strip(), str(draft_id).strip())
        record = self._tips.get(key)
        if record is None:
            raise FormsBuilderDraftNotFoundError(
                details={"tenant_id": key[0], "draft_id": key[1]},
            )
        return DraftRecord(
            tenant_id=record.tenant_id,
            draft_id=record.draft_id,
            revision=record.revision,
            status=record.status,
            form_id=record.form_id,
            composition_contract=record.composition_contract,
            composition=copy.deepcopy(record.composition),
        )

    def update(
        self,
        *,
        tenant_id: str,
        draft_id: str,
        composition: FormDraftComposition,
        expected_revision: int,
        registry: FieldCatalogRegistry | None = None,
        require_valid: bool = True,
    ) -> DraftRecord:
        current = self.get(tenant_id=tenant_id, draft_id=draft_id)
        if current.status == STATUS_ARCHIVED:
            raise FormsBuilderDraftArchivedError(
                details={"draft_id": draft_id, "revision": current.revision},
            )
        if composition.draft_id != current.draft_id:
            raise FormsBuilderCompositionInvalidError(
                details={
                    "reason": "draft_id_mismatch",
                    "expected": current.draft_id,
                    "got": composition.draft_id,
                },
            )
        if int(expected_revision) != current.revision:
            raise FormsBuilderDraftConflictError(
                details={
                    "draft_id": draft_id,
                    "expected_revision": int(expected_revision),
                    "current_revision": current.revision,
                },
            )
        payload = _serialize_composition(
            composition, registry=registry, require_valid=require_valid
        )
        new_rev = current.revision + 1
        updated = DraftRecord(
            tenant_id=current.tenant_id,
            draft_id=current.draft_id,
            revision=new_rev,
            status=STATUS_ACTIVE,
            form_id=current.form_id,
            composition_contract=BUILDER_COMPOSITION_CONTRACT,
            composition=payload,
        )
        self._tips[(current.tenant_id, current.draft_id)] = updated
        self._revisions[(current.tenant_id, current.draft_id, new_rev)] = copy.deepcopy(payload)
        return updated

    def list(
        self,
        *,
        tenant_id: str,
        include_archived: bool = False,
    ) -> list[DraftRecord]:
        tid = str(tenant_id).strip()
        rows = [r for (t, _), r in self._tips.items() if t == tid]
        if not include_archived:
            rows = [r for r in rows if r.status == STATUS_ACTIVE]
        rows.sort(key=lambda r: r.draft_id)
        return [
            DraftRecord(
                tenant_id=r.tenant_id,
                draft_id=r.draft_id,
                revision=r.revision,
                status=r.status,
                form_id=r.form_id,
                composition_contract=r.composition_contract,
                composition=copy.deepcopy(r.composition),
            )
            for r in rows
        ]

    def archive(
        self,
        *,
        tenant_id: str,
        draft_id: str,
        expected_revision: int,
    ) -> DraftRecord:
        current = self.get(tenant_id=tenant_id, draft_id=draft_id)
        if current.status == STATUS_ARCHIVED:
            raise FormsBuilderDraftArchivedError(
                details={"draft_id": draft_id, "revision": current.revision},
            )
        if int(expected_revision) != current.revision:
            raise FormsBuilderDraftConflictError(
                details={
                    "draft_id": draft_id,
                    "expected_revision": int(expected_revision),
                    "current_revision": current.revision,
                },
            )
        archived = DraftRecord(
            tenant_id=current.tenant_id,
            draft_id=current.draft_id,
            revision=current.revision,
            status=STATUS_ARCHIVED,
            form_id=current.form_id,
            composition_contract=current.composition_contract,
            composition=copy.deepcopy(current.composition),
        )
        self._tips[(current.tenant_id, current.draft_id)] = archived
        return archived

    def get_revision_payload(
        self,
        *,
        tenant_id: str,
        draft_id: str,
        revision: int,
    ) -> dict[str, Any]:
        key = (str(tenant_id).strip(), str(draft_id).strip(), int(revision))
        payload = self._revisions.get(key)
        if payload is None:
            raise FormsBuilderDraftNotFoundError(
                details={
                    "tenant_id": key[0],
                    "draft_id": key[1],
                    "revision": key[2],
                },
            )
        return copy.deepcopy(payload)


# --- SQLAlchemy persistence (durable Draft tip; not Forms Adapter) ---


async def create_draft(
    session: AsyncSession,
    *,
    tenant_id: str,
    composition: FormDraftComposition,
    form_id: str | None = None,
    registry: FieldCatalogRegistry | None = None,
    require_valid: bool = True,
) -> DraftRecord:
    tid = str(tenant_id or "").strip()
    if not tid:
        raise FormsBuilderCompositionInvalidError(details={"reason": "empty_tenant_id"})
    existing = await session.scalar(
        select(FormBuilderDraft).where(
            FormBuilderDraft.tenant_id == tid,
            FormBuilderDraft.draft_id == composition.draft_id,
        )
    )
    if existing is not None:
        raise FormsBuilderDraftConflictError(
            details={"reason": "draft_already_exists", "draft_id": composition.draft_id},
        )
    payload = _serialize_composition(
        composition, registry=registry, require_valid=require_valid
    )
    now = now_utc()
    tip = FormBuilderDraft(
        tenant_id=tid,
        draft_id=composition.draft_id,
        form_id=str(form_id).strip() if form_id else None,
        revision=1,
        status=STATUS_ACTIVE,
        composition_contract=BUILDER_COMPOSITION_CONTRACT,
        composition=payload,
        created_at=now,
        updated_at=now,
    )
    session.add(tip)
    session.add(
        FormBuilderDraftRevision(
            tenant_id=tid,
            draft_id=composition.draft_id,
            revision=1,
            composition_contract=BUILDER_COMPOSITION_CONTRACT,
            composition=copy.deepcopy(payload),
            created_at=now,
        )
    )
    await session.flush()
    return _record_from_row(tip)


async def get_draft(
    session: AsyncSession,
    *,
    tenant_id: str,
    draft_id: str,
) -> DraftRecord:
    row = await session.scalar(
        select(FormBuilderDraft).where(
            FormBuilderDraft.tenant_id == str(tenant_id).strip(),
            FormBuilderDraft.draft_id == str(draft_id).strip(),
        )
    )
    if row is None:
        raise FormsBuilderDraftNotFoundError(
            details={"tenant_id": tenant_id, "draft_id": draft_id},
        )
    return _record_from_row(row)


async def update_draft(
    session: AsyncSession,
    *,
    tenant_id: str,
    draft_id: str,
    composition: FormDraftComposition,
    expected_revision: int,
    registry: FieldCatalogRegistry | None = None,
    require_valid: bool = True,
) -> DraftRecord:
    row = await session.scalar(
        select(FormBuilderDraft).where(
            FormBuilderDraft.tenant_id == str(tenant_id).strip(),
            FormBuilderDraft.draft_id == str(draft_id).strip(),
        )
    )
    if row is None:
        raise FormsBuilderDraftNotFoundError(
            details={"tenant_id": tenant_id, "draft_id": draft_id},
        )
    if row.status == STATUS_ARCHIVED:
        raise FormsBuilderDraftArchivedError(
            details={"draft_id": draft_id, "revision": int(row.revision)},
        )
    if composition.draft_id != row.draft_id:
        raise FormsBuilderCompositionInvalidError(
            details={
                "reason": "draft_id_mismatch",
                "expected": row.draft_id,
                "got": composition.draft_id,
            },
        )
    if int(expected_revision) != int(row.revision):
        raise FormsBuilderDraftConflictError(
            details={
                "draft_id": draft_id,
                "expected_revision": int(expected_revision),
                "current_revision": int(row.revision),
            },
        )
    payload = _serialize_composition(
        composition, registry=registry, require_valid=require_valid
    )
    new_rev = int(row.revision) + 1
    now = now_utc()
    row.revision = new_rev
    row.composition = payload
    row.composition_contract = BUILDER_COMPOSITION_CONTRACT
    row.updated_at = now
    session.add(
        FormBuilderDraftRevision(
            tenant_id=str(row.tenant_id),
            draft_id=str(row.draft_id),
            revision=new_rev,
            composition_contract=BUILDER_COMPOSITION_CONTRACT,
            composition=copy.deepcopy(payload),
            created_at=now,
        )
    )
    await session.flush()
    return _record_from_row(row)


async def list_drafts(
    session: AsyncSession,
    *,
    tenant_id: str,
    include_archived: bool = False,
) -> list[DraftRecord]:
    stmt = select(FormBuilderDraft).where(
        FormBuilderDraft.tenant_id == str(tenant_id).strip()
    )
    if not include_archived:
        stmt = stmt.where(FormBuilderDraft.status == STATUS_ACTIVE)
    stmt = stmt.order_by(FormBuilderDraft.draft_id.asc())
    rows = (await session.scalars(stmt)).all()
    return [_record_from_row(r) for r in rows]


async def archive_draft(
    session: AsyncSession,
    *,
    tenant_id: str,
    draft_id: str,
    expected_revision: int,
) -> DraftRecord:
    row = await session.scalar(
        select(FormBuilderDraft).where(
            FormBuilderDraft.tenant_id == str(tenant_id).strip(),
            FormBuilderDraft.draft_id == str(draft_id).strip(),
        )
    )
    if row is None:
        raise FormsBuilderDraftNotFoundError(
            details={"tenant_id": tenant_id, "draft_id": draft_id},
        )
    if row.status == STATUS_ARCHIVED:
        raise FormsBuilderDraftArchivedError(
            details={"draft_id": draft_id, "revision": int(row.revision)},
        )
    if int(expected_revision) != int(row.revision):
        raise FormsBuilderDraftConflictError(
            details={
                "draft_id": draft_id,
                "expected_revision": int(expected_revision),
                "current_revision": int(row.revision),
            },
        )
    row.status = STATUS_ARCHIVED
    row.updated_at = now_utc()
    await session.flush()
    return _record_from_row(row)


async def get_draft_revision(
    session: AsyncSession,
    *,
    tenant_id: str,
    draft_id: str,
    revision: int,
) -> dict[str, Any]:
    row = await session.scalar(
        select(FormBuilderDraftRevision).where(
            FormBuilderDraftRevision.tenant_id == str(tenant_id).strip(),
            FormBuilderDraftRevision.draft_id == str(draft_id).strip(),
            FormBuilderDraftRevision.revision == int(revision),
        )
    )
    if row is None:
        raise FormsBuilderDraftNotFoundError(
            details={
                "tenant_id": tenant_id,
                "draft_id": draft_id,
                "revision": int(revision),
            },
        )
    return copy.deepcopy(dict(row.composition or {}))
