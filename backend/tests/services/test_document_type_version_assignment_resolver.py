"""Tests for document type version assignment resolver."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.services.document_type_version_assignment_resolver import (
    DocumentTypeVersionAssignmentResolver,
    VersionAssignmentStatus,
)


def _version(*, vid: str, valid_from: date, valid_to: date | None = None, schema: dict | None = None):
    ver = MagicMock()
    ver.id = vid
    ver.version_code = "v1"
    ver.valid_from = valid_from
    ver.valid_to = valid_to
    ver.schema_json = {} if schema is None else schema
    return ver


def _doc_type(*, tid: str = "type-1", code: str = "passport"):
    doc_type = MagicMock()
    doc_type.id = tid
    doc_type.code = code
    return doc_type


def _scalars_first(item):
    result = MagicMock()
    scalars = MagicMock()
    scalars.first = MagicMock(return_value=item)
    result.scalars = MagicMock(return_value=scalars)
    return result


def _scalars_all(items):
    result = MagicMock()
    result.scalars = MagicMock(return_value=iter(items))
    return result


@pytest.mark.anyio
async def test_existing_version_preserved() -> None:
    db = AsyncMock()
    doc = MagicMock()
    doc.doc_type = "passport"
    doc.document_type_version_id = "ver-existing"
    doc.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    ver = _version(vid="ver-existing", valid_from=date(2020, 1, 1))
    doc_type = _doc_type()
    db.execute = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=(ver, doc_type))))

    result = await DocumentTypeVersionAssignmentResolver.resolve_for_document(db, doc)
    assert result.status == VersionAssignmentStatus.existing
    assert result.document_type_version_id == "ver-existing"


@pytest.mark.anyio
async def test_ambiguous_when_multiple_date_compatible_versions() -> None:
    db = AsyncMock()
    doc = MagicMock()
    doc.doc_type = "passport"
    doc.document_type_version_id = None
    doc.document_type_id = None
    doc.meta = {}
    doc.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)

    doc_type = _doc_type()
    v1 = _version(vid="v1", valid_from=date(2023, 1, 1), valid_to=date(2025, 12, 31))
    v2 = _version(vid="v2", valid_from=date(2024, 1, 1), valid_to=None)

    db.execute = AsyncMock(
        side_effect=[
            _scalars_first(doc_type),
            _scalars_all([v1, v2]),
        ]
    )
    result = await DocumentTypeVersionAssignmentResolver.resolve_for_document(db, doc)
    assert result.status == VersionAssignmentStatus.ambiguous
    assert len(result.compatible_version_ids) >= 2


@pytest.mark.anyio
async def test_single_compatible_version_resolved() -> None:
    db = AsyncMock()
    doc = MagicMock()
    doc.doc_type = "passport"
    doc.document_type_version_id = None
    doc.meta = {}
    doc.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)

    doc_type = _doc_type()
    v1 = _version(vid="v1", valid_from=date(2020, 1, 1))

    db.execute = AsyncMock(
        side_effect=[
            _scalars_first(doc_type),
            _scalars_all([v1]),
        ]
    )
    result = await DocumentTypeVersionAssignmentResolver.resolve_for_document(db, doc)
    assert result.status == VersionAssignmentStatus.resolved
    assert result.document_type_version_id == "v1"


@pytest.mark.anyio
async def test_current_catalog_selection_skips_future_and_uses_latest_applicable() -> None:
    db = AsyncMock()
    doc_type = _doc_type()
    future = _version(vid="future", valid_from=date(2027, 1, 1))
    current = _version(vid="current", valid_from=date(2025, 6, 1))
    older = _version(vid="older", valid_from=date(2020, 1, 1))
    result = MagicMock()
    result.all = MagicMock(
        return_value=[
            (doc_type, future),
            (doc_type, current),
            (doc_type, older),
        ]
    )
    db.execute = AsyncMock(return_value=result)

    selected = (
        await DocumentTypeVersionAssignmentResolver.list_current_applicable_versions(
            db,
            as_of=date(2026, 10, 8),
        )
    )

    assert len(selected) == 1
    assert selected[0].document_type is doc_type
    assert selected[0].version is current
