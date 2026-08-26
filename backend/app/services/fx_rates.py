"""Official FX rates for Overview Marketing (and other display conversion).

Source of truth: Narodowy Bank Polski table A mid rates (PLN per 1 foreign unit).
Cross rates (USD↔EUR) are derived via PLN. No third-party FX ledger — display only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping, Optional

import httpx

NBP_TABLE_A_URL = "https://api.nbp.pl/api/exchangerates/tables/A/?format=json"
SUPPORTED = frozenset({"USD", "PLN", "EUR"})
MONEY_QUANT = Decimal("0.01")
_CACHE_TTL_SEC = 3600.0


@dataclass(frozen=True)
class FxBundle:
    as_of: str
    provider: str
    """Mid quote: units of PLN per 1 unit of currency (PLN=1)."""
    pln_per_unit: Mapping[str, Decimal]

    def to_dict(self) -> dict:
        return {
            "as_of": self.as_of,
            "provider": self.provider,
            "base": "PLN",
            "pln_per_unit": {k: str(v) for k, v in self.pln_per_unit.items()},
            "supported": sorted(SUPPORTED),
        }


class FxRatesError(RuntimeError):
    pass


_cache_bundle: Optional[FxBundle] = None
_cache_expires_at: float = 0.0


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _normalize(code: str) -> str:
    c = str(code or "").strip().upper()
    if c not in SUPPORTED:
        raise FxRatesError(f"unsupported currency: {code!r}")
    return c


async def fetch_nbp_table_a(*, force_refresh: bool = False) -> FxBundle:
    """Fetch (or return cached) NBP table A mids for USD/EUR + PLN=1."""
    global _cache_bundle, _cache_expires_at
    now = time.monotonic()
    if (
        not force_refresh
        and _cache_bundle is not None
        and now < _cache_expires_at
    ):
        return _cache_bundle

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(NBP_TABLE_A_URL)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:  # noqa: BLE001 — surface as FX error
        if _cache_bundle is not None:
            # Stale cache beats hard failure for display conversion.
            return _cache_bundle
        raise FxRatesError(f"NBP rates unavailable: {exc}") from exc

    if not isinstance(payload, list) or not payload:
        raise FxRatesError("NBP response empty")
    table = payload[0] if isinstance(payload[0], dict) else {}
    as_of = str(table.get("effectiveDate") or "").strip() or "unknown"
    rates_list = table.get("rates") or []
    by_code: dict[str, Decimal] = {"PLN": Decimal("1")}
    for row in rates_list:
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip().upper()
        if code not in {"USD", "EUR"}:
            continue
        mid = row.get("mid")
        try:
            by_code[code] = Decimal(str(mid))
        except Exception as exc:  # noqa: BLE001
            raise FxRatesError(f"invalid NBP mid for {code}: {mid!r}") from exc

    if "USD" not in by_code or "EUR" not in by_code:
        raise FxRatesError("NBP table A missing USD or EUR")

    bundle = FxBundle(as_of=as_of, provider="NBP", pln_per_unit=by_code)
    _cache_bundle = bundle
    _cache_expires_at = now + _CACHE_TTL_SEC
    return bundle


def convert_amount(
    amount: Decimal | str | int | float,
    *,
    from_currency: str,
    to_currency: str,
    bundle: FxBundle,
) -> Decimal:
    """Convert amount using NBP mid cross via PLN."""
    src = _normalize(from_currency)
    dst = _normalize(to_currency)
    amt = Decimal(str(amount))
    if src == dst:
        return _money(amt)
    src_pln = Decimal(bundle.pln_per_unit[src])
    dst_pln = Decimal(bundle.pln_per_unit[dst])
    if dst_pln <= 0:
        raise FxRatesError(f"invalid PLN mid for {dst}")
    return _money(amt * src_pln / dst_pln)


def rate(
    *,
    from_currency: str,
    to_currency: str,
    bundle: FxBundle,
) -> Decimal:
    """Units of ``to_currency`` per 1 ``from_currency``."""
    return convert_amount(
        Decimal("1"),
        from_currency=from_currency,
        to_currency=to_currency,
        bundle=bundle,
    )


def rates_matrix(bundle: FxBundle, currencies: Iterable[str] | None = None) -> dict[str, dict[str, str]]:
    codes = [_normalize(c) for c in (currencies or SUPPORTED)]
    out: dict[str, dict[str, str]] = {}
    for src in codes:
        out[src] = {
            dst: str(rate(from_currency=src, to_currency=dst, bundle=bundle)) for dst in codes
        }
    return out


__all__ = [
    "FxBundle",
    "FxRatesError",
    "SUPPORTED",
    "convert_amount",
    "fetch_nbp_table_a",
    "rate",
    "rates_matrix",
]
