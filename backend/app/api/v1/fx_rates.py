"""FX rates API — NBP mid rates for display currency conversion."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.services.fx_rates import (
    FxRatesError,
    convert_amount,
    fetch_nbp_table_a,
    rates_matrix,
)

router = APIRouter(prefix="/fx", tags=["fx"])


class FxRatesOut(BaseModel):
    as_of: str
    provider: str = "NBP"
    base: str = "PLN"
    supported: List[str]
    pln_per_unit: dict[str, str]
    """Quote matrix: rates[from][to] = units of `to` per 1 `from`."""
    rates: dict[str, dict[str, str]]


class FxConvertOut(BaseModel):
    amount: str
    from_currency: str
    to_currency: str
    converted: str
    as_of: str
    provider: str = "NBP"
    rate: str = Field(description="Units of to_currency per 1 from_currency")


@router.get("/rates", response_model=FxRatesOut)
async def get_fx_rates(
    refresh: bool = Query(False, description="Bypass cache and refetch NBP"),
    _user: UserCtx = Depends(get_current_user),
) -> FxRatesOut:
    try:
        bundle = await fetch_nbp_table_a(force_refresh=refresh)
    except FxRatesError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return FxRatesOut(
        as_of=bundle.as_of,
        provider=bundle.provider,
        base="PLN",
        supported=sorted(bundle.pln_per_unit.keys()),
        pln_per_unit={k: str(v) for k, v in bundle.pln_per_unit.items()},
        rates=rates_matrix(bundle),
    )


@router.get("/convert", response_model=FxConvertOut)
async def convert_fx(
    amount: str = Query(..., description="Amount in from_currency"),
    from_currency: str = Query("USD", alias="from"),
    to_currency: str = Query("PLN", alias="to"),
    refresh: bool = Query(False),
    _user: UserCtx = Depends(get_current_user),
) -> FxConvertOut:
    try:
        bundle = await fetch_nbp_table_a(force_refresh=refresh)
        converted = convert_amount(
            amount, from_currency=from_currency, to_currency=to_currency, bundle=bundle
        )
        unit = convert_amount(
            "1", from_currency=from_currency, to_currency=to_currency, bundle=bundle
        )
    except FxRatesError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return FxConvertOut(
        amount=str(amount),
        from_currency=from_currency.strip().upper(),
        to_currency=to_currency.strip().upper(),
        converted=str(converted),
        as_of=bundle.as_of,
        provider=bundle.provider,
        rate=str(unit),
    )
