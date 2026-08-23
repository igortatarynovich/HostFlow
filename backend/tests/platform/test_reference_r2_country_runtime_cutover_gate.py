"""Reference R2 — Country Runtime Cutover Gate.

Runtime /catalogs country+dial lists and the frontend COUNTRY_CODES set are
projections of the Country Registry. XK is not a runtime identity. Q1–Q2.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from backend.app.constants.catalogs import COUNTRIES, DIAL_CODES
from backend.app.reference.country_registry import (
    FORBIDDEN_IDENTITY_CODES,
    ISO_3166_1_ASSIGNED_COUNT,
    country_registry_alpha2_set,
    list_country_registry_entries,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_CATALOGS = _REPO_ROOT / "backend" / "app" / "constants" / "catalogs.py"
_FRONTEND = _REPO_ROOT / "hostflow-frontend" / "src" / "data" / "countries.ts"


def test_r2_runtime_countries_match_registry() -> None:
    alpha2 = country_registry_alpha2_set()
    assert len(COUNTRIES) == ISO_3166_1_ASSIGNED_COUNT
    assert set(COUNTRIES) == alpha2
    assert alpha2.isdisjoint(FORBIDDEN_IDENTITY_CODES)
    by_code = {e.identity.alpha2: e for e in list_country_registry_entries()}
    assert COUNTRIES["PL"] == by_code["PL"].labels.ru
    assert DIAL_CODES["PL"] == by_code["PL"].classifications.dial_code
    assert DIAL_CODES == {
        e.identity.alpha2: e.classifications.dial_code
        for e in list_country_registry_entries()
    }


def test_r2_catalogs_py_is_projection_not_second_sot() -> None:
    source = _CATALOGS.read_text(encoding="utf-8")
    assert "list_country_registry_entries" in source
    tree = ast.parse(source)
    hardcoded = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        and any(
            isinstance(k, ast.Constant) and k.value == "XK" for k in node.keys
        )
    ]
    assert hardcoded == []
    assert '"XK"' not in source and "'XK'" not in source


def test_r2_frontend_country_codes_match_registry() -> None:
    text = _FRONTEND.read_text(encoding="utf-8")
    match = re.search(
        r"const COUNTRY_CODES:\s*string\[\]\s*=\s*\[(.*?)]",
        text,
        flags=re.S,
    )
    assert match is not None
    codes = re.findall(r"'([A-Z]{2})'", match.group(1))
    assert len(codes) == ISO_3166_1_ASSIGNED_COUNT
    assert set(codes) == country_registry_alpha2_set()
    assert "XK" not in codes


def test_r2_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Reference R2 Country Runtime Cutover Gate" in ci
    assert "test_reference_r2_country_runtime_cutover_gate.py" in ci
    r1_at = ci.index("Reference R1 Country Registry Gate")
    r2_at = ci.index("Reference R2 Country Runtime Cutover Gate")
    lint_at = ci.index("- name: Lint")
    assert r1_at < r2_at < lint_at


def test_r2_gate_filename() -> None:
    assert Path(__file__).name == "test_reference_r2_country_runtime_cutover_gate.py"
