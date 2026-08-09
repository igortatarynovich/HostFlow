from __future__ import annotations

from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id
from backend.app.services.search_acquisition_service import (
    LegacyLaunchDisabledError,
    add_acquisition_activity,
    build_acquisition_snapshot,
    get_vacancy_or_raise,
    perform_acquisition_activity_action,
    persist_acquisition_snapshot,
    update_acquisition_audience,
)


def _raise_legacy_launch(exc: LegacyLaunchDisabledError) -> None:
    raise HTTPException(
        status_code=410,
        detail={
            "code": "legacy_launch_disabled",
            "message": (
                "Legacy Подборы acquisition writes are disabled. "
                "Use Marketing Campaign → Flight instead."
            ),
            "search_id": exc.search_id,
            "marketing_setup_path": exc.marketing_setup_path,
        },
    )

router = APIRouter(tags=["vacancies-acquisition"])


class AcquisitionActivityCreateIn(BaseModel):
    type: Literal["meta", "google", "tiktok", "telegram", "referral", "public_link", "qr"] = "meta"
    name: str = Field(min_length=2, max_length=160)


class AcquisitionAudienceIn(BaseModel):
    countries: list[str] = Field(default_factory=list)
    age_min: Optional[int] = Field(default=None, ge=16, le=80)
    age_max: Optional[int] = Field(default=None, ge=16, le=80)
    experience: Optional[str] = None
    languages: list[str] = Field(default_factory=list)
    gender: Optional[str] = None
    interests: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class AcquisitionReconciliationOut(BaseModel):
    status: str
    linked_campaign_id: Optional[str] = None
    linked_campaign_name: Optional[str] = None
    linked_campaign_status: Optional[str] = None
    candidate_campaign_ids: list[str] = Field(default_factory=list)
    reason: Optional[str] = None


class AcquisitionSnapshotOut(BaseModel):
    version: int = 2
    synced_at: Optional[str] = None
    search_fill: dict[str, Any] = Field(default_factory=dict)
    activities: list[dict[str, Any]] = Field(default_factory=list)
    channels: list[dict[str, Any]] = Field(default_factory=list)
    attention: list[dict[str, Any]] = Field(default_factory=list)
    journal: list[dict[str, Any]] = Field(default_factory=list)
    overview: dict[str, Any] = Field(default_factory=dict)
    audience: dict[str, Any] = Field(default_factory=dict)
    analytics: dict[str, Any] = Field(default_factory=dict)
    sync: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    legacy_mode: bool = True
    reconciliation: Optional[AcquisitionReconciliationOut] = None
    marketing_setup_path: Optional[str] = None


class AcquisitionActivityActionIn(BaseModel):
    action: Literal["pause", "resume", "archive", "duplicate", "update_bindings"]
    search_ids: list[str] = Field(default_factory=list)


@router.get("/{vacancy_id}/acquisition", response_model=AcquisitionSnapshotOut)
async def get_search_acquisition(
    vacancy_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    _own_company_id: str = Depends(resolve_active_own_company_id),
    _user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    try:
        vacancy = await get_vacancy_or_raise(db, str(tenant_id), str(vacancy_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    snapshot = await build_acquisition_snapshot(db, str(tenant_id), vacancy, sync_meta=False)
    return AcquisitionSnapshotOut.model_validate(snapshot)


@router.post("/{vacancy_id}/acquisition/sync", response_model=AcquisitionSnapshotOut)
async def sync_search_acquisition(
    vacancy_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    _own_company_id: str = Depends(resolve_active_own_company_id),
    _user: UserCtx = Depends(require_trust_write()),
):
    db, tenant_id = db_tenant
    try:
        vacancy = await get_vacancy_or_raise(db, str(tenant_id), str(vacancy_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    sync_error: Optional[str] = None
    try:
        snapshot = await build_acquisition_snapshot(db, str(tenant_id), vacancy, sync_meta=True)
    except Exception as exc:
        sync_error = str(exc)
        snapshot = await build_acquisition_snapshot(
            db, str(tenant_id), vacancy, sync_meta=False, sync_error=sync_error
        )
        snapshot["sync"] = {
            **(snapshot.get("sync") or {}),
            "last_sync_at": snapshot.get("synced_at"),
            "last_sync_error": sync_error,
        }
    await persist_acquisition_snapshot(db, vacancy, snapshot)
    await db.commit()
    return AcquisitionSnapshotOut.model_validate(snapshot)


@router.post("/{vacancy_id}/acquisition/activities", response_model=dict)
@router.post("/{vacancy_id}/acquisition/channels", response_model=dict)
async def create_search_acquisition_activity(
    vacancy_id: UUID,
    payload: AcquisitionActivityCreateIn,
    db_tenant=Depends(get_db_with_tenant),
    _own_company_id: str = Depends(resolve_active_own_company_id),
    _user: UserCtx = Depends(require_trust_write()),
):
    db, tenant_id = db_tenant
    try:
        vacancy = await get_vacancy_or_raise(db, str(tenant_id), str(vacancy_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    try:
        activity = await add_acquisition_activity(
            db,
            str(tenant_id),
            vacancy,
            channel_type=payload.type,
            name=payload.name,
        )
    except LegacyLaunchDisabledError as exc:
        _raise_legacy_launch(exc)
    await db.commit()
    return activity


@router.put("/{vacancy_id}/acquisition/audience", response_model=dict)
async def put_search_acquisition_audience(
    vacancy_id: UUID,
    payload: AcquisitionAudienceIn,
    db_tenant=Depends(get_db_with_tenant),
    _own_company_id: str = Depends(resolve_active_own_company_id),
    _user: UserCtx = Depends(require_trust_write()),
):
    db, tenant_id = db_tenant
    try:
        vacancy = await get_vacancy_or_raise(db, str(tenant_id), str(vacancy_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    try:
        audience = await update_acquisition_audience(
            db,
            str(tenant_id),
            vacancy,
            payload.model_dump(exclude_none=True),
        )
    except LegacyLaunchDisabledError as exc:
        _raise_legacy_launch(exc)
    await db.commit()
    return audience


@router.post("/{vacancy_id}/acquisition/activities/{activity_id}/actions", response_model=AcquisitionSnapshotOut)
async def post_search_acquisition_activity_action(
    vacancy_id: UUID,
    activity_id: str,
    payload: AcquisitionActivityActionIn,
    db_tenant=Depends(get_db_with_tenant),
    _own_company_id: str = Depends(resolve_active_own_company_id),
    _user: UserCtx = Depends(require_trust_write()),
):
    db, tenant_id = db_tenant
    try:
        vacancy = await get_vacancy_or_raise(db, str(tenant_id), str(vacancy_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    try:
        result = await perform_acquisition_activity_action(
            db,
            str(tenant_id),
            vacancy,
            activity_id,
            payload.action,
            search_ids=payload.search_ids or None,
        )
    except LegacyLaunchDisabledError as exc:
        _raise_legacy_launch(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="Activity not found")
    except ValueError as exc:
        code = str(exc)
        if code == "static_activity":
            raise HTTPException(status_code=400, detail="Cannot modify system activity")
        if code == "search_ids_required":
            raise HTTPException(status_code=400, detail="search_ids required")
        raise HTTPException(status_code=400, detail="Invalid action")
    await db.commit()
    return AcquisitionSnapshotOut.model_validate(result["snapshot"])
