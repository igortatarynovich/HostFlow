"""Stage 6 PR-6a — Outcome commercial value delivery contract.

V1 SoT is a ``declared_v1`` snapshot on completed ``CampaignOutcome``.
Analytics must read via this contract; it must not invent amounts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.outcome_service import STATUS_COMPLETED
from backend.app.models.campaign import CampaignOutcome

SOURCE_DECLARED_V1 = "declared_v1"
_ALLOWED_SOURCES = frozenset({SOURCE_DECLARED_V1})

ZERO = Decimal("0")
MONEY_QUANT = Decimal("0.0001")


class OutcomeCommercialValueError(ValueError):
    """Outcome commercial value contract violation."""


@dataclass(frozen=True)
class OutcomeCommercialValueRead:
    outcome_id: str
    amount: Decimal
    currency: str
    source: str
    as_of: datetime

    def to_dict(self) -> dict:
        return {
            "outcome_id": self.outcome_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "source": self.source,
            "as_of": self.as_of.isoformat(),
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _normalize_currency(code: str) -> str:
    c = str(code or "").strip().upper()
    if len(c) != 3 or not c.isalpha():
        raise OutcomeCommercialValueError(f"invalid currency: {code!r}")
    return c


def _from_row(row: CampaignOutcome) -> Optional[OutcomeCommercialValueRead]:
    if row.commercial_value_amount is None or not row.commercial_value_currency:
        return None
    if not row.commercial_value_set_at:
        return None
    return OutcomeCommercialValueRead(
        outcome_id=str(row.id),
        amount=_money(Decimal(row.commercial_value_amount)),
        currency=_normalize_currency(str(row.commercial_value_currency)),
        source=str(row.commercial_value_source or SOURCE_DECLARED_V1),
        as_of=row.commercial_value_set_at,
    )


async def get_outcome_commercial_value(
    db: AsyncSession,
    *,
    tenant_id: str,
    outcome_id: str,
) -> Optional[OutcomeCommercialValueRead]:
    row = await db.get(CampaignOutcome, str(outcome_id))
    if row is None or str(row.tenant_id) != str(tenant_id):
        return None
    return _from_row(row)


async def list_outcome_commercial_values(
    db: AsyncSession,
    *,
    tenant_id: str,
    outcome_ids: Sequence[str] | Iterable[str],
) -> dict[str, OutcomeCommercialValueRead]:
    ids = [str(x).strip() for x in outcome_ids if str(x).strip()]
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(CampaignOutcome).where(
                CampaignOutcome.tenant_id == str(tenant_id),
                CampaignOutcome.id.in_(ids),
            )
        )
    ).scalars().all()
    out: dict[str, OutcomeCommercialValueRead] = {}
    for row in rows:
        read = _from_row(row)
        if read is not None:
            out[str(row.id)] = read
    return out


async def set_outcome_commercial_value(
    db: AsyncSession,
    *,
    tenant_id: str,
    outcome_id: str,
    amount: Decimal | str | int | float,
    currency: str,
    source: str = SOURCE_DECLARED_V1,
) -> OutcomeCommercialValueRead:
    """Only writer of ``commercial_value_*`` on ``CampaignOutcome``."""
    row = await db.get(CampaignOutcome, str(outcome_id))
    if row is None or str(row.tenant_id) != str(tenant_id):
        raise OutcomeCommercialValueError("outcome not found for tenant")
    if str(row.status) != STATUS_COMPLETED:
        raise OutcomeCommercialValueError(
            "commercial value allowed only on completed outcomes"
        )

    src = str(source or "").strip() or SOURCE_DECLARED_V1
    if src not in _ALLOWED_SOURCES:
        raise OutcomeCommercialValueError(f"unsupported value source: {src!r}")

    amt = _money(Decimal(str(amount)))
    if amt <= ZERO:
        raise OutcomeCommercialValueError("commercial value amount must be > 0")

    cur = _normalize_currency(currency)
    as_of = _now()
    row.commercial_value_amount = amt
    row.commercial_value_currency = cur
    row.commercial_value_source = src
    row.commercial_value_set_at = as_of
    await db.flush()
    return OutcomeCommercialValueRead(
        outcome_id=str(row.id),
        amount=amt,
        currency=cur,
        source=src,
        as_of=as_of,
    )
