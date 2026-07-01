"""Downstream prep using trusted employment identity adapter (PR7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.employment_identity_read_adapter import (
    CONSUMER_CLIENT_FORM,
    CONSUMER_CONTRACT_GENERATION,
    CONSUMER_EXPORT,
    CONSUMER_PAYROLL_PREP,
    CONSUMER_PERMIT_APPLICATION,
    CONSUMER_ZUS_PREPARATION,
    TrustedEmploymentIdentityRead,
    TrustedIdentityAccessError,
    get_trusted_employment_identity_for_employee,
)


@dataclass(frozen=True)
class DownstreamIdentityPrepResult:
    ready: bool
    blocked: bool
    consumer: str
    block_code: Optional[str] = None
    projection_status: Optional[str] = None
    review_id: Optional[str] = None
    bindings: dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "blocked": self.blocked,
            "consumer": self.consumer,
            "block_code": self.block_code,
            "projection_status": self.projection_status,
            "review_id": self.review_id,
            "bindings": dict(self.bindings),
            "message": self.message,
        }


class DownstreamIdentityBlockedError(Exception):
    """Payroll / API layer: trusted identity not available for this consumer."""

    def __init__(self, result: DownstreamIdentityPrepResult):
        self.result = result
        super().__init__(result.block_code or "TRUSTED_IDENTITY_DENIED")


def identity_attributes_to_bindings(attributes: dict[str, Optional[str]]) -> dict[str, Any]:
    """Map canonical employment identity attributes to flat template/prep bindings."""
    legal_name = str(attributes.get("legal_name") or "").strip()
    parts = legal_name.split(None, 1)
    return {
        "legal_name": legal_name or None,
        "legal_first_name": parts[0] if parts else None,
        "legal_last_name": parts[1] if len(parts) > 1 else None,
        "birth_date": attributes.get("birth_date"),
        "citizenship": attributes.get("citizenship"),
        "pesel": attributes.get("pesel"),
        "passport_number": attributes.get("passport_number"),
        "residence_basis": attributes.get("residence_basis"),
        "permit_type": attributes.get("permit_type"),
        "permit_expiry": attributes.get("permit_expiry"),
        "driver_license_categories": attributes.get("driver_license_categories"),
        "code95_expiry": attributes.get("code95_expiry"),
        "medical_expiry": attributes.get("medical_expiry"),
        "psychotests_expiry": attributes.get("psychotests_expiry"),
    }


def bindings_from_trusted_read(trusted: TrustedEmploymentIdentityRead) -> dict[str, Any]:
    return identity_attributes_to_bindings(trusted.attributes)


def apply_trusted_identity_merge_variables(
    ctx: dict[str, Any], bindings: dict[str, Any]
) -> None:
    """Expose ``trusted_identity.*`` for merge templates (PR8)."""
    namespace = {k: v for k, v in bindings.items() if v is not None}
    ctx["trusted_identity"] = namespace
    for key, value in namespace.items():
        ctx.setdefault("bindings", {})[f"trusted_identity.{key}"] = value
    ctx["bindings"].update(namespace)


async def _evaluate(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    consumer: str,
) -> DownstreamIdentityPrepResult:
    try:
        trusted = await get_trusted_employment_identity_for_employee(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            consumer=consumer,
            raise_on_denied=True,
        )
        return DownstreamIdentityPrepResult(
            ready=True,
            blocked=False,
            consumer=consumer,
            projection_status=trusted.projection_status,
            review_id=trusted.review_id,
            bindings=bindings_from_trusted_read(trusted),
        )
    except TrustedIdentityAccessError as exc:
        return DownstreamIdentityPrepResult(
            ready=False,
            blocked=True,
            consumer=consumer,
            block_code=exc.code,
            projection_status=exc.projection_status,
            review_id=exc.review_id,
            message=str(exc),
        )
    except ValueError as exc:
        code = str(exc)
        if code in ("EMPLOYEE_NOT_FOUND", "HR_REVIEW_NOT_FOUND"):
            return DownstreamIdentityPrepResult(
                ready=False,
                blocked=True,
                consumer=consumer,
                block_code=code,
                message=code,
            )
        raise


async def evaluate_zus_preparation(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> DownstreamIdentityPrepResult:
    return await _evaluate(
        db, tenant_id=tenant_id, employee_id=employee_id, consumer=CONSUMER_ZUS_PREPARATION
    )


async def evaluate_payroll_preparation(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> DownstreamIdentityPrepResult:
    return await _evaluate(
        db, tenant_id=tenant_id, employee_id=employee_id, consumer=CONSUMER_PAYROLL_PREP
    )


async def evaluate_contract_merge_identity(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> DownstreamIdentityPrepResult:
    return await _evaluate(
        db, tenant_id=tenant_id, employee_id=employee_id, consumer=CONSUMER_CONTRACT_GENERATION
    )


async def evaluate_permit_application(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> DownstreamIdentityPrepResult:
    return await _evaluate(
        db, tenant_id=tenant_id, employee_id=employee_id, consumer=CONSUMER_PERMIT_APPLICATION
    )


async def evaluate_export_identity(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> DownstreamIdentityPrepResult:
    return await _evaluate(
        db, tenant_id=tenant_id, employee_id=employee_id, consumer=CONSUMER_EXPORT
    )


async def evaluate_client_form_identity(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> DownstreamIdentityPrepResult:
    return await _evaluate(
        db, tenant_id=tenant_id, employee_id=employee_id, consumer=CONSUMER_CLIENT_FORM
    )
