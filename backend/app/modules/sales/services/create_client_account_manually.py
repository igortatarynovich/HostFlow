"""Origins v1 — create_client_account_manually (Sales-owned).

origin_type = manual_creation. No Lead, SalesInquiry, Flights, or Convert Mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.client_account import ClientAccount
from backend.app.modules.client_accounts import crud
from backend.app.services.audit import log_activity

ORIGIN_MANUAL_CREATION = "manual_creation"
CREATION_ORIGIN_CONTRACT = "client_account.creation_origin.v1"

DUPLICATE_ACTION_OPEN_EXISTING = "open_existing"
DUPLICATE_ACTION_CREATE_NEW = "create_new"
DUPLICATE_ACTION_CANCEL = "cancel"


class ManualClientAccountError(Exception):
    code = "manual_client_account_error"

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.reason = str(reason)
        self.details = details or {}


class ManualClientAccountDuplicateError(ManualClientAccountError):
    code = "manual_client_account_duplicate"

    def __init__(
        self,
        message: str,
        *,
        candidates: Sequence[dict[str, Any]],
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            reason="duplicate_match_requires_decision",
            details={**(details or {}), "candidates": list(candidates)},
        )
        self.candidates = list(candidates)


@dataclass(frozen=True, slots=True)
class ManualClientAccountResult:
    account: ClientAccount
    creation_ref: str
    idempotency_key: str
    idempotent_replay: bool
    origin_type: str = ORIGIN_MANUAL_CREATION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trim(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _normalize_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


async def _assert_company_tenant(db: AsyncSession, *, tenant_id: str, company_id: str) -> None:
    from backend.app.models import Company

    row = await db.scalar(
        select(Company.id).where(Company.id == company_id, Company.tenant_id == tenant_id).limit(1)
    )
    if row is None:
        raise ManualClientAccountError(
            "Company not found in tenant",
            reason="company_not_in_tenant",
            details={"company_id": company_id},
        )


async def find_manual_create_duplicates(
    db: AsyncSession,
    *,
    tenant_id: str,
    display_name: str,
    own_company_id: Optional[str],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Strong match = exact normalized display_name within tenant / own_company scope."""
    needle = _normalize_name(display_name)
    if not needle:
        return []
    stmt = select(ClientAccount).where(ClientAccount.tenant_id == tenant_id)
    if own_company_id:
        stmt = stmt.where(ClientAccount.own_company_id == own_company_id)
    rows = (await db.execute(stmt.limit(500))).scalars().all()
    hits: list[dict[str, Any]] = []
    for row in rows:
        if _normalize_name(str(row.display_name or "")) != needle:
            continue
        hits.append(
            {
                "client_account_id": str(row.id),
                "display_name": str(row.display_name),
                "status": str(row.status),
                "match_kind": "display_name_exact",
            }
        )
        if len(hits) >= max(1, min(limit, 20)):
            break
    return hits


async def _load_by_idempotency(
    db: AsyncSession,
    *,
    tenant_id: str,
    idempotency_key: str,
) -> Optional[ClientAccount]:
    return await db.scalar(
        select(ClientAccount)
        .where(
            ClientAccount.tenant_id == tenant_id,
            ClientAccount.idempotency_key == idempotency_key,
        )
        .limit(1)
    )


async def create_client_account_manually(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str],
    actor_user_id: str,
    display_name: str,
    status: str = "prospect",
    owner_user_id: Optional[str] = None,
    primary_company_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    reason: Optional[str] = None,
    source_note: Optional[str] = None,
    force_create: bool = False,
    duplicate_decision: Optional[dict[str, Any]] = None,
) -> ManualClientAccountResult:
    """Canonical manual ClientAccount create (Origins v1).

    Forbidden: Lead, SalesInquiry, Flights, Convert Mapping, inventing source_lead_id.
    """
    tid = _trim(tenant_id)
    actor = _trim(actor_user_id)
    name = _trim(display_name)
    if not tid:
        raise ManualClientAccountError("tenant_id is required", reason="missing_tenant")
    if not actor:
        raise ManualClientAccountError("actor_user_id is required", reason="missing_actor")
    if not name:
        raise ManualClientAccountError("display_name is required", reason="missing_display_name")

    oc = _trim(own_company_id)
    key = _trim(idempotency_key) or f"manual-{uuid4()}"
    existing = await _load_by_idempotency(db, tenant_id=tid, idempotency_key=key)
    if existing is not None:
        return ManualClientAccountResult(
            account=existing,
            creation_ref=str(existing.creation_ref or existing.id),
            idempotency_key=str(existing.idempotency_key or key),
            idempotent_replay=True,
        )

    if primary_company_id:
        await _assert_company_tenant(db, tenant_id=tid, company_id=str(primary_company_id))

    candidates = await find_manual_create_duplicates(
        db, tenant_id=tid, display_name=name, own_company_id=oc
    )
    decision = dict(duplicate_decision) if isinstance(duplicate_decision, dict) else {}
    decision_action = _trim(decision.get("action"))

    if candidates and not force_create:
        raise ManualClientAccountDuplicateError(
            "Existing ClientAccount match requires operator decision",
            candidates=candidates,
            details={"match_count": len(candidates)},
        )

    if candidates and force_create:
        if decision_action == DUPLICATE_ACTION_CANCEL:
            raise ManualClientAccountError(
                "duplicate decision cancel — no create",
                reason="duplicate_cancelled",
                details={"candidates": candidates},
            )
        if decision_action == DUPLICATE_ACTION_OPEN_EXISTING:
            raise ManualClientAccountError(
                "open_existing selected — use existing ClientAccount id",
                reason="open_existing_required",
                details={
                    "candidates": candidates,
                    "client_account_id": decision.get("client_account_id")
                    or (candidates[0].get("client_account_id") if candidates else None),
                },
            )
        if decision_action != DUPLICATE_ACTION_CREATE_NEW:
            raise ManualClientAccountError(
                "force_create requires duplicate_decision.action=create_new",
                reason="missing_duplicate_decision",
                details={"candidates": candidates},
            )

    creation_ref = str(uuid4())
    created_at = _now()
    origin_record = {
        "contract": CREATION_ORIGIN_CONTRACT,
        "origin_type": ORIGIN_MANUAL_CREATION,
        "creation_ref": creation_ref,
        "idempotency_key": key,
        "actor_user_id": actor,
        "tenant_id": tid,
        "own_company_id": oc,
        "created_at": created_at,
        "reason": _trim(reason),
        "source_note": _trim(source_note),
        "duplicate_decision": decision or None,
        "duplicate_candidates_snapshot": candidates if candidates else None,
    }

    account = ClientAccount(
        id=crud.new_client_account_id(),
        tenant_id=tid,
        own_company_id=oc,
        display_name=name,
        status=_trim(status) or "prospect",
        owner_user_id=_trim(owner_user_id),
        primary_company_id=_trim(primary_company_id),
        source_lead_id=None,  # INV-CAO-03 / Origins §5.2 — never invent
        origin_type=ORIGIN_MANUAL_CREATION,
        creation_ref=creation_ref,
        idempotency_key=key,
        creation_origin_v1=origin_record,
    )
    db.add(account)
    await db.flush()

    try:
        # SAVEPOINT so FK/audit failures do not abort the outer create transaction.
        async with db.begin_nested():
            await log_activity(
                db,
                tenant_id=tid,
                actor_id=actor,
                action="client_account.manual_creation",
                target_type="client_account",
                target_id=str(account.id),
                payload={
                    "origin_type": ORIGIN_MANUAL_CREATION,
                    "creation_ref": creation_ref,
                    "idempotency_key": key,
                    "own_company_id": oc,
                    "display_name": name,
                    "force_create": bool(force_create),
                    "duplicate_decision": decision or None,
                    "candidate_count": len(candidates),
                },
            )
    except Exception:
        # Audit must not roll back a successful create; fail-open for audit only.
        pass

    return ManualClientAccountResult(
        account=account,
        creation_ref=creation_ref,
        idempotency_key=key,
        idempotent_replay=False,
    )
