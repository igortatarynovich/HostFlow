from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.object_storage import get_object_storage, normalize_key
from backend.app.models import Candidate, MergeDocumentGenerationLog, WorkforceEmployee
from backend.app.modules.documents import crud as documents_crud
from backend.app.services.document_catalog import normalize_doc_type
from backend.app.services.document_merge.context import build_merge_context
from backend.app.services.document_merge.render import render_merge_text
from backend.app.services.document_merge.templates_repo import (
    get_template,
    resolve_template_for_scope,
)


def _snapshot_context(ctx: Dict[str, Any], *, max_chars: int = 12000) -> Dict[str, Any]:
    try:
        raw = json.dumps(ctx, default=str)
    except Exception:
        raw = "{}"
    if len(raw) > max_chars:
        return {"truncated": True, "preview": raw[:max_chars]}
    return json.loads(raw)


def _suffix_for_mime(mime: str) -> str:
    m = (mime or "").lower()
    if "html" in m:
        return ".html"
    return ".txt"


async def generate_merge_document(
    session: AsyncSession,
    tenant_id: str,
    *,
    template_id: Optional[str] = None,
    template_code: Optional[str] = None,
    candidate_id: Optional[str] = None,
    workforce_employee_id: Optional[str] = None,
    variable_bindings: Optional[Dict[str, Any]] = None,
    triggered_by_user_id: Optional[str] = None,
) -> Tuple[MergeDocumentGenerationLog, Any]:
    employee: Optional[WorkforceEmployee] = None
    candidate: Optional[Candidate] = None

    if workforce_employee_id:
        employee = await session.get(WorkforceEmployee, workforce_employee_id)
        if not employee or employee.tenant_id != tenant_id:
            raise ValueError("workforce_employee_not_found")
        if employee.candidate_id:
            candidate = await session.get(Candidate, employee.candidate_id)
            if candidate and candidate.tenant_id != tenant_id:
                candidate = None

    if candidate_id:
        cand = await session.get(Candidate, candidate_id)
        if not cand or cand.tenant_id != tenant_id:
            raise ValueError("candidate_not_found")
        candidate = cand

    if candidate is None and employee is None:
        raise ValueError("candidate_or_employee_required")

    template = None
    if template_id:
        template = await get_template(session, tenant_id, template_id)
    elif template_code:
        oc_scope = None
        if employee is not None:
            oc_scope = employee.own_company_id
        elif candidate is not None:
            oc_scope = candidate.own_company_id
        template = await resolve_template_for_scope(
            session, tenant_id, template_code.strip(), own_company_id=oc_scope
        )
    if template is None:
        raise ValueError("template_not_found")

    merged_bindings: Dict[str, Any] = {}
    if isinstance(template.variable_bindings, dict):
        merged_bindings.update(template.variable_bindings)
    if variable_bindings:
        merged_bindings.update(variable_bindings)

    ctx = await build_merge_context(
        session,
        tenant_id,
        candidate=candidate,
        employee=employee,
        extra_bindings=merged_bindings,
    )

    identity_meta = ctx.get("identity") if isinstance(ctx.get("identity"), dict) else {}
    if employee is not None and identity_meta.get("blocked"):
        code = str(identity_meta.get("block_code") or "TRUSTED_IDENTITY_DENIED")
        raise ValueError(code)

    rendered = render_merge_text(
        template.body_text,
        context=ctx,
        variable_bindings=merged_bindings,
    )
    pattern = template.output_filename_pattern or "{{ candidate.full_name }}_{{ template.code }}"
    filename = render_merge_text(
        pattern,
        context={
            **ctx,
            "template": {
                "code": template.code,
                "name": template.name,
            },
        },
        variable_bindings=merged_bindings,
    ).strip() or f"{template.code}{_suffix_for_mime(template.output_mime)}"
    filename = Path(filename).name  # drop path segments
    if not Path(filename).suffix:
        filename = f"{filename}{_suffix_for_mime(template.output_mime)}"

    storage = get_object_storage()
    key = normalize_key(f"merge_generated/{tenant_id}/{template.id}/{datetime.now(timezone.utc).timestamp()}-{filename}")
    body_bytes = rendered.encode("utf-8")
    saved = await storage.save_bytes(
        key,
        body_bytes,
        content_type=template.output_mime or "text/plain",
    )
    public_url = storage.public_url(normalize_key(saved.key))
    entry = {
        "name": filename,
        "url": public_url,
        "size": saved.size,
        "mime": template.output_mime or "text/plain",
        "storage_path": normalize_key(saved.key),
        "uploaded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "uploaded_by": triggered_by_user_id,
        "version": 1,
    }

    doc_type = normalize_doc_type(template.doc_type or "additional_document")
    cand_id = candidate.id if candidate else None
    if not cand_id:
        raise ValueError("candidate_required_for_document")

    meta = {
        "title": template.name,
        "description": f"Generated from merge template {template.code} ({template.name}).",
        "merge_generated": True,
        "merge_template_id": template.id,
        "merge_template_code": template.code,
    }

    own_co = None
    if employee is not None:
        own_co = employee.own_company_id
    if candidate is not None:
        own_co = own_co or candidate.own_company_id

    doc = await documents_crud.create_document(
        session,
        {
            "tenant_id": tenant_id,
            "candidate_id": cand_id,
            "own_company_id": own_co,
            "doc_type": doc_type,
            "custom_name": template.name,
            "user_comment": f"merge:{template.code}",
            "files": [entry],
            "meta": meta,
            "source": "merge_template",
        },
    )

    log = MergeDocumentGenerationLog(
        tenant_id=tenant_id,
        template_id=template.id,
        candidate_id=cand_id,
        workforce_employee_id=employee.id if employee else None,
        document_id=doc.id,
        triggered_by_user_id=triggered_by_user_id,
        status="success",
        error_message=None,
        context_snapshot=_snapshot_context(ctx),
    )
    session.add(log)
    await session.flush()
    await session.refresh(log)
    return log, doc
