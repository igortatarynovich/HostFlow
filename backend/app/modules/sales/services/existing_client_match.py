"""Match a Sales inquiry company name to an existing client Company.

Operators see Clients as ``companies`` (role client). Meta forms often omit the
legal suffix (``Synergia Kadry`` vs ``SYNERGIA KADRY sp. z o.o.``), so convert
must not propose a second client for the same firm.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Company
from backend.app.models.client_account import ClientAccount

_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")

# Longest-first token suffixes stripped from the *end* of a normalized name.
_LEGAL_SUFFIXES: tuple[tuple[str, ...], ...] = (
    ("spolka", "z", "ograniczona", "odpowiedzialnoscia"),
    ("spolka", "z", "o", "o"),
    ("sp", "z", "o", "o"),
    ("sp", "z", "oo"),
    ("sp", "zoo"),
    ("s", "a"),
    ("s", "c"),
    ("ltd",),
    ("llc",),
    ("gmbh",),
    ("inc",),
    ("corp",),
    ("plc",),
    ("bv",),
    ("ag",),
)

_MIN_KEY_LEN = 4


def _trim(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


_PL_TRANSLIT = str.maketrans(
    {
        "ł": "l",
        "Ł": "l",
        "ą": "a",
        "Ą": "a",
        "ć": "c",
        "Ć": "c",
        "ę": "e",
        "Ę": "e",
        "ń": "n",
        "Ń": "n",
        "ó": "o",
        "Ó": "o",
        "ś": "s",
        "Ś": "s",
        "ź": "z",
        "Ź": "z",
        "ż": "z",
        "Ż": "z",
    }
)


def normalize_company_match_key(value: str) -> str:
    """Casefold + strip accents + drop legal-form suffixes."""
    raw = unicodedata.normalize("NFKD", str(value or "").translate(_PL_TRANSLIT))
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = raw.casefold()
    raw = _PUNCT_RE.sub(" ", raw)
    tokens = [tok for tok in _SPACE_RE.split(raw) if tok]
    if not tokens:
        return ""
    changed = True
    while changed and tokens:
        changed = False
        for suffix in _LEGAL_SUFFIXES:
            n = len(suffix)
            if len(tokens) > n and tuple(tokens[-n:]) == suffix:
                tokens = tokens[:-n]
                changed = True
                break
    return " ".join(tokens)


@dataclass(frozen=True, slots=True)
class ExistingClientHit:
    company_id: str
    name: str
    client_account_id: Optional[str] = None
    match_kind: str = "company_name"

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "company_id": self.company_id,
            "name": self.name,
            "match_kind": self.match_kind,
        }
        if self.client_account_id:
            out["client_account_id"] = self.client_account_id
        return out


def _is_operating_company(row: Company) -> bool:
    extra = row.extra if isinstance(getattr(row, "extra", None), dict) else {}
    role = str(extra.get("company_role") or extra.get("company_kind") or "client").strip().lower()
    return role == "operating"


def _hit_from_company(row: Company) -> ExistingClientHit:
    account_id = _trim(getattr(row, "client_account_id", None))
    return ExistingClientHit(
        company_id=str(row.id),
        name=str(row.name or "").strip() or str(row.legal_name or "").strip(),
        client_account_id=account_id,
        match_kind="company_name",
    )


async def find_existing_client_hits(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_name: str,
    own_company_id: Optional[str] = None,
    limit: int = 8,
) -> list[ExistingClientHit]:
    """Return client companies whose normalized name equals the inquiry name."""
    needle = normalize_company_match_key(company_name)
    if len(needle) < _MIN_KEY_LEN:
        return []
    tid = _trim(tenant_id)
    if not tid:
        return []

    companies = (
        await db.execute(
            select(Company)
            .where(Company.tenant_id == tid, Company.is_archived.is_(False))
            .limit(800)
        )
    ).scalars().all()

    hits: list[ExistingClientHit] = []
    seen: set[str] = set()
    for row in companies:
        if _is_operating_company(row):
            continue
        keys = {
            normalize_company_match_key(str(row.name or "")),
            normalize_company_match_key(str(row.legal_name or "")),
        }
        keys.discard("")
        if needle not in keys:
            continue
        cid = str(row.id)
        if cid in seen:
            continue
        seen.add(cid)
        hits.append(_hit_from_company(row))
        if len(hits) >= limit:
            break

    if hits:
        return hits

    # Fallback: ClientAccount.display_name (may differ from Company.name after a rename).
    stmt = select(ClientAccount).where(ClientAccount.tenant_id == tid)
    oc = _trim(own_company_id)
    if oc:
        stmt = stmt.where(ClientAccount.own_company_id == oc)
    accounts = (await db.execute(stmt.limit(500))).scalars().all()
    for account in accounts:
        if normalize_company_match_key(str(account.display_name or "")) != needle:
            continue
        primary = _trim(getattr(account, "primary_company_id", None))
        if not primary:
            continue
        company = await db.scalar(
            select(Company).where(Company.id == primary, Company.tenant_id == tid)
        )
        if company is None or bool(getattr(company, "is_archived", False)):
            continue
        cid = str(company.id)
        if cid in seen:
            continue
        seen.add(cid)
        hits.append(
            ExistingClientHit(
                company_id=cid,
                name=str(company.name or account.display_name),
                client_account_id=str(account.id),
                match_kind="client_account_display_name",
            )
        )
        if len(hits) >= limit:
            break
    return hits


async def find_unique_existing_client(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_name: str,
    own_company_id: Optional[str] = None,
) -> Optional[ExistingClientHit]:
    hits = await find_existing_client_hits(
        db,
        tenant_id=tenant_id,
        company_name=company_name,
        own_company_id=own_company_id,
        limit=2,
    )
    if len(hits) == 1:
        return hits[0]
    return None
