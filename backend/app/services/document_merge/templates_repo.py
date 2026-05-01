from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import MergeDocumentTemplate


async def list_templates(
    session: AsyncSession,
    tenant_id: str,
    *,
    include_inactive: bool = False,
    own_company_id: Optional[str] = None,
) -> List[MergeDocumentTemplate]:
    stmt = select(MergeDocumentTemplate).where(MergeDocumentTemplate.tenant_id == tenant_id)
    if not include_inactive:
        stmt = stmt.where(MergeDocumentTemplate.is_active.is_(True))
    oc = (own_company_id or "").strip() or None
    if oc:
        stmt = stmt.where(
            (MergeDocumentTemplate.own_company_id == oc) | (MergeDocumentTemplate.own_company_id.is_(None))
        )
    stmt = stmt.order_by(MergeDocumentTemplate.code.asc(), MergeDocumentTemplate.name.asc())
    return list((await session.execute(stmt)).scalars().all())


async def get_template(session: AsyncSession, tenant_id: str, template_id: str) -> Optional[MergeDocumentTemplate]:
    stmt = select(MergeDocumentTemplate).where(
        MergeDocumentTemplate.id == template_id,
        MergeDocumentTemplate.tenant_id == tenant_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def resolve_template_for_scope(
    session: AsyncSession,
    tenant_id: str,
    code: str,
    *,
    own_company_id: Optional[str],
) -> Optional[MergeDocumentTemplate]:
    code_s = (code or "").strip()
    if not code_s:
        return None
    oc = (own_company_id or "").strip() or None
    if oc:
        stmt = select(MergeDocumentTemplate).where(
            MergeDocumentTemplate.tenant_id == tenant_id,
            MergeDocumentTemplate.code == code_s,
            MergeDocumentTemplate.own_company_id == oc,
            MergeDocumentTemplate.is_active.is_(True),
        )
        hit = (await session.execute(stmt)).scalar_one_or_none()
        if hit:
            return hit
    stmt = select(MergeDocumentTemplate).where(
        MergeDocumentTemplate.tenant_id == tenant_id,
        MergeDocumentTemplate.code == code_s,
        MergeDocumentTemplate.own_company_id.is_(None),
        MergeDocumentTemplate.is_active.is_(True),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def create_template(
    session: AsyncSession,
    tenant_id: str,
    payload: Dict[str, Any],
) -> MergeDocumentTemplate:
    oc_raw = payload.get("own_company_id")
    oc = str(oc_raw).strip() if oc_raw else None
    row = MergeDocumentTemplate(
        tenant_id=tenant_id,
        own_company_id=oc or None,
        code=str(payload["code"]).strip(),
        name=str(payload["name"]).strip(),
        description=(payload.get("description") or None),
        body_text=str(payload["body_text"]),
        output_mime=str(payload.get("output_mime") or "text/plain").strip() or "text/plain",
        variable_bindings=payload.get("variable_bindings") if isinstance(payload.get("variable_bindings"), dict) else None,
        output_filename_pattern=(payload.get("output_filename_pattern") or None),
        doc_type=str(payload.get("doc_type") or "additional_document").strip(),
        is_active=bool(payload.get("is_active", True)),
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def update_template(
    session: AsyncSession,
    tenant_id: str,
    template_id: str,
    payload: Dict[str, Any],
) -> Optional[MergeDocumentTemplate]:
    row = await get_template(session, tenant_id, template_id)
    if row is None:
        return None
    if "own_company_id" in payload:
        oc_raw = payload.get("own_company_id")
        row.own_company_id = str(oc_raw).strip() if oc_raw else None
    if "code" in payload and payload["code"] is not None:
        row.code = str(payload["code"]).strip()
    if "name" in payload and payload["name"] is not None:
        row.name = str(payload["name"]).strip()
    if "description" in payload:
        row.description = payload.get("description")
    if "body_text" in payload and payload["body_text"] is not None:
        row.body_text = str(payload["body_text"])
    if "output_mime" in payload and payload["output_mime"] is not None:
        row.output_mime = str(payload["output_mime"]).strip() or "text/plain"
    if "variable_bindings" in payload:
        vb = payload.get("variable_bindings")
        row.variable_bindings = vb if isinstance(vb, dict) else None
    if "output_filename_pattern" in payload:
        row.output_filename_pattern = payload.get("output_filename_pattern")
    if "doc_type" in payload and payload["doc_type"] is not None:
        row.doc_type = str(payload["doc_type"]).strip()
    if "is_active" in payload:
        row.is_active = bool(payload["is_active"])
    await session.flush()
    await session.refresh(row)
    return row


async def delete_template(session: AsyncSession, tenant_id: str, template_id: str) -> bool:
    row = await get_template(session, tenant_id, template_id)
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True
