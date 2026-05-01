"""Phase 2.1.B — keep `docs/specs/plans-matrix.md` §2–§3 in sync with backend constants.

Parses markdown pipe-tables and asserts equality with `PLAN_LICENSE_LIMITS`,
`PLAN_LEADS_MONTHLY_LIMIT`, portal monthly caps, catalog prices, and `PLAN_CODES`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.app.api.v1.settings.billing._helpers.plans import PLAN_CODES, PLAN_LICENSE_LIMITS
from backend.app.services.lead_quota import PLAN_LEADS_MONTHLY_LIMIT
from backend.app.services import portal_candidate_usage


_REPO_ROOT = Path(__file__).resolve().parents[2]
_PLANS_MATRIX = _REPO_ROOT / "docs" / "specs" / "plans-matrix.md"

_PLAN_ORDER = ("starter", "team", "pro", "enterprise")


def _cell_int(cell: str) -> int | None:
    s = cell.strip()
    if not s or s.upper() == "TBD":
        return None
    if s in ("—", "-", "–", "N/A", "n/a"):
        return None
    s = s.replace(" ", "").replace("\u00a0", "")
    if not s or not s[0].isdigit() and not (s.startswith("-") and len(s) > 1 and s[1].isdigit()):
        return None
    return int(s)


def _extract_section(text: str, heading: str) -> str:
    """Return lines from `heading` (e.g. '## 2.') until the next `## ` heading."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith(heading):
            start = i + 1
            break
    if start is None:
        raise AssertionError(f"Section {heading!r} not found in plans-matrix.md")
    out: list[str] = []
    for line in lines[start:]:
        if line.startswith("## ") and not line.startswith(heading):
            break
        out.append(line)
    return "\n".join(out)


def _parse_limits_table(
    section: str,
) -> dict[str, tuple[int | None, int | None, int | None, int | None]]:
    """First column = limit key (backticks); next four = Solo, Team, Business, Enterprise."""
    out: dict[str, tuple[int | None, int | None, int | None, int | None]] = {}
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("|-------") or "Лимит |" in line or "| Лимит " in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 5:
            continue
        key_m = re.search(r"`([^`]+)`", parts[0])
        if not key_m:
            continue
        key = key_m.group(1).strip()
        solo, team, biz, ent = (
            _cell_int(parts[1]),
            _cell_int(parts[2]),
            _cell_int(parts[3]),
            _cell_int(parts[4]),
        )
        out[key] = (solo, team, biz, ent)
    return out


def _parse_monthly_table(
    section: str,
) -> dict[str, tuple[int | None, int | None, int | None, int | None]]:
    """Rows: first column label, then Solo / Team / Business / Enterprise."""
    out: dict[str, tuple[int | None, int | None, int | None, int | None]] = {}
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("|-------") or "| Квота " in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 5:
            continue
        label = parts[0]
        if "Trial" in label or "trial" in label.lower():
            continue
        solo, team, biz, ent = (
            _cell_int(parts[1]),
            _cell_int(parts[2]),
            _cell_int(parts[3]),
            _cell_int(parts[4]),
        )
        if label.startswith("Inbound leads"):
            out["inbound_leads_monthly"] = (solo, team, biz, ent)
        elif "portal" in label.lower() and "candidate" in label.lower():
            out["portal_active_monthly"] = (solo, team, biz, ent)
    return out


def _read_matrix() -> str:
    if not _PLANS_MATRIX.is_file():
        pytest.skip(f"Missing {_PLANS_MATRIX}")
    return _PLANS_MATRIX.read_text(encoding="utf-8")


def test_plans_matrix_file_exists() -> None:
    assert _PLANS_MATRIX.is_file(), f"Expected {_PLANS_MATRIX}"


def test_plan_codes_match_matrix_section1() -> None:
    text = _read_matrix()
    m = re.search(r"`PLAN_CODES`.*?:\s*`(\([^)]+\))`", text)
    assert m, "Document should list PLAN_CODES tuple in §1"
    # e.g. ("starter", "team", "pro")
    raw = m.group(1)
    codes = tuple(x.strip().strip("'\"") for x in raw.strip("()").split(","))
    assert codes == PLAN_CODES


def test_section2_limits_match_plan_license_limits() -> None:
    text = _read_matrix()
    sec = _extract_section(text, "## 2.")
    parsed = _parse_limits_table(sec)
    assert parsed, "No limit rows parsed from §2"
    for key, (solo, team, biz, ent) in parsed.items():
        assert key in PLAN_LICENSE_LIMITS["starter"], f"Unknown limit key in MD: {key}"
        row = {k: PLAN_LICENSE_LIMITS[k][key] for k in _PLAN_ORDER}
        assert row["starter"] == solo, f"{key} starter: MD {solo} vs code {row['starter']}"
        assert row["team"] == team, f"{key} team: MD {team} vs code {row['team']}"
        assert row["pro"] == biz, f"{key} pro: MD {biz} vs code {row['pro']}"
        assert row["enterprise"] == ent, f"{key} enterprise: MD {ent} vs code {row['enterprise']}"


def test_section3_monthly_quotas_match_services() -> None:
    text = _read_matrix()
    sec = _extract_section(text, "## 3.")
    parsed = _parse_monthly_table(sec)
    assert "inbound_leads_monthly" in parsed
    solo, team, biz, ent = parsed["inbound_leads_monthly"]
    assert solo == PLAN_LEADS_MONTHLY_LIMIT["starter"]
    assert team == PLAN_LEADS_MONTHLY_LIMIT["team"]
    assert biz == PLAN_LEADS_MONTHLY_LIMIT["pro"]
    assert ent == PLAN_LEADS_MONTHLY_LIMIT["enterprise"]

    assert "portal_active_monthly" in parsed
    ps, pt, pb, pe = parsed["portal_active_monthly"]
    assert ps is None
    assert portal_candidate_usage.monthly_cap_for_plan_code("starter") is None
    assert pt == portal_candidate_usage.monthly_cap_for_plan_code("team") == 300
    assert pb == portal_candidate_usage.monthly_cap_for_plan_code("pro") == 2000
    assert pe == portal_candidate_usage.monthly_cap_for_plan_code("enterprise") == 2000


def test_available_plans_catalog_prices_match_matrix_section1() -> None:
    """§1 table: starter 29/24, team 129/109, pro 249/219 (EUR)."""
    text = _read_matrix()
    # Lines like | `starter` | **Solo** | 29 | 24 |
    for code, month_eur, year_eq in (
        ("starter", 29, 24),
        ("team", 129, 109),
        ("pro", 249, 219),
    ):
        pat = rf"\|\s*`{code}`\s*\|[^|]+\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
        m = re.search(pat, text)
        assert m, f"§1 pricing row for {code} not found"
        assert int(m.group(1)) == month_eur
        assert int(m.group(2)) == year_eq

    from backend.app.api.v1.settings.billing._helpers.plans import _available_plans

    plans = {p.code: p for p in _available_plans()}
    for code, month_eur, year_eq in (
        ("starter", 29, 24),
        ("team", 129, 109),
        ("pro", 249, 219),
    ):
        po = plans[code]
        assert po.monthly_price_usd == month_eur
        assert po.yearly_equivalent_monthly_eur == year_eq
