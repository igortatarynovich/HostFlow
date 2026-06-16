from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.deps import PUBLIC_LEGACY_DEFAULT_TENANT_UUID, get_db
from backend.app.models.tenant import Tenant
from backend.app.services.legal_documents import get_active_legal_document

router = APIRouter(tags=["public-legal"])

_SLUG_TO_DOC_TYPE: dict[str, str] = {
    "rodo": "rodo_clause",
    "privacy": "privacy_policy",
    "terms": "terms_of_service",
    "cookies": "cookie_policy",
}


def _resolve_tenant_id(raw: str | None) -> str:
    value = (raw or "").strip()
    if not value:
        return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)


def _normalize_host(raw: str | None) -> str:
    host = (raw or "").strip().lower()
    if not host:
        return ""
    if "," in host:
        host = host.split(",", 1)[0].strip()
    if ":" in host:
        host = host.split(":", 1)[0].strip()
    return host


def _collect_tenant_hosts(settings_obj: object) -> set[str]:
    if not isinstance(settings_obj, dict):
        return set()
    out: set[str] = set()
    single_keys = ("public_domain", "custom_domain", "legal_domain")
    list_keys = ("public_hosts", "domains", "legal_hosts")
    for key in single_keys:
        host = _normalize_host(str(settings_obj.get(key) or ""))
        if host:
            out.add(host)
    for key in list_keys:
        raw = settings_obj.get(key)
        if isinstance(raw, list):
            for item in raw:
                host = _normalize_host(str(item or ""))
                if host:
                    out.add(host)
    return out


async def _resolve_tenant_id_from_host(db: AsyncSession, request: Request) -> str:
    xf_host = _normalize_host(request.headers.get("x-forwarded-host"))
    req_host = _normalize_host(getattr(request.url, "hostname", None))
    host = xf_host or req_host
    if not host:
        return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)

    frontend_host = ""
    try:
        frontend_host = _normalize_host(str(getattr(settings, "frontend_url", "") or "").split("://", 1)[-1].split("/", 1)[0])
    except Exception:
        frontend_host = ""
    if frontend_host and host == frontend_host:
        return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)

    rows = (
        await db.execute(select(Tenant.id, Tenant.settings).where(Tenant.is_active.is_(True)))
    ).all()
    for tenant_id, tenant_settings in rows:
        if host in _collect_tenant_hosts(tenant_settings):
            return str(tenant_id)
    return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
    try:
        return str(UUID(value))
    except Exception:
        return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)


def _render_document_page(title: str, version_id: str, body_html: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
  </head>
  <body>
    <main style="max-width:920px;margin:2rem auto;padding:0 1rem;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;">
      <header style="margin-bottom:1rem;padding-bottom:.75rem;border-bottom:1px solid #e2e8f0;">
        <h1 style="margin:0;font-size:1.5rem;">{title}</h1>
        <p style="margin:.5rem 0 0;color:#475569;">Version: {version_id}</p>
      </header>
      {body_html}
    </main>
  </body>
</html>"""


@router.get("/legal/{slug}.html")
@router.get("/api/v1/public/legal/{slug}.html")
async def public_legal_page(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
    tenant_id_header: str | None = Header(None, alias="X-Tenant-Id"),
    tenant_id_query: str | None = Query(None, alias="tenant_id"),
):
    doc_type = _SLUG_TO_DOC_TYPE.get((slug or "").strip().lower())
    if not doc_type:
        fallback = Path("/app/public/legal") / f"{slug}.html"
        if fallback.is_file():
            return FileResponse(str(fallback))
        return HTMLResponse("<h1>Not found</h1>", status_code=404)

    explicit_tenant = _resolve_tenant_id(tenant_id_header or tenant_id_query)
    tenant_id = (
        explicit_tenant
        if explicit_tenant != str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID) or (tenant_id_header or tenant_id_query)
        else await _resolve_tenant_id_from_host(db, request)
    )
    doc = await get_active_legal_document(db, tenant_id, doc_type)
    if doc is not None:
        html = (doc.content_html or "").strip()
        if html:
            page = _render_document_page(
                title=f"Legal document: {slug}",
                version_id=str(doc.version_id or ""),
                body_html=html,
            )
            return HTMLResponse(page, headers={"Cache-Control": "no-store"})
        link = (doc.content_url or "").strip()
        if link:
            return RedirectResponse(link, status_code=302)

    fallback = Path("/app/public/legal") / f"{slug}.html"
    if fallback.is_file():
        return FileResponse(str(fallback))
    return HTMLResponse("<h1>Not found</h1>", status_code=404)
