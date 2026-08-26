"""NBP mid FX conversion (display) — USD / PLN / EUR."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.services.fx_rates import (
    FxBundle,
    FxRatesError,
    convert_amount,
    fetch_nbp_table_a,
    rate,
)


def _bundle() -> FxBundle:
    return FxBundle(
        as_of="2026-08-05",
        provider="NBP",
        pln_per_unit={
            "PLN": Decimal("1"),
            "USD": Decimal("3.732"),
            "EUR": Decimal("4.305"),
        },
    )


def test_convert_usd_to_pln():
    assert convert_amount("100", from_currency="USD", to_currency="PLN", bundle=_bundle()) == Decimal(
        "373.20"
    )


def test_convert_usd_to_eur():
    # 100 * 3.732 / 4.305 ≈ 86.69
    assert convert_amount("100", from_currency="USD", to_currency="EUR", bundle=_bundle()) == Decimal(
        "86.69"
    )


def test_convert_same_currency():
    assert convert_amount("12.345", from_currency="usd", to_currency="USD", bundle=_bundle()) == Decimal(
        "12.35"
    )


def test_rate_eur_to_usd():
    assert rate(from_currency="EUR", to_currency="USD", bundle=_bundle()) == Decimal("1.15")


def test_unsupported_currency():
    with pytest.raises(FxRatesError):
        convert_amount("1", from_currency="USD", to_currency="GBP", bundle=_bundle())


@pytest.mark.asyncio
async def test_fetch_nbp_table_a_parses_payload():
    payload = [
        {
            "effectiveDate": "2026-08-05",
            "rates": [
                {"code": "USD", "mid": 3.732},
                {"code": "EUR", "mid": 4.305},
                {"code": "GBP", "mid": 4.9},
            ],
        }
    ]

    mock_resp = AsyncMock()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json = lambda: payload

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=mock_resp)

    # Reset module cache
    import backend.app.services.fx_rates as fx_mod

    fx_mod._cache_bundle = None
    fx_mod._cache_expires_at = 0.0

    with patch("backend.app.services.fx_rates.httpx.AsyncClient", return_value=mock_client):
        bundle = await fetch_nbp_table_a(force_refresh=True)

    assert bundle.as_of == "2026-08-05"
    assert bundle.pln_per_unit["USD"] == Decimal("3.732")
    assert bundle.pln_per_unit["EUR"] == Decimal("4.305")
    assert bundle.pln_per_unit["PLN"] == Decimal("1")
