"""Post-PMI Kernel public-contract preflight gate.

Locks PASS of the five-module public-contract probe (Recruitment → Employment →
Boundary → Documents → Workforce) after Ready composition remediation.

Does not open dual zero-policy, P1→P6, or PEM-1.
"""

from __future__ import annotations

import ast
import importlib
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "post-pmi-kernel-public-contract-preflight.md"
_READY_PUBLIC = (
    _REPO_ROOT / "backend" / "app" / "modules" / "recruitment" / "public" / "ready.py"
)
_OWNED_FIX = (
    _REPO_ROOT
    / "docs"
    / "specs"
    / "tasks"
    / "recruitment-ready-policy-composition-separation.md"
)
_GATE = Path(__file__)


def test_kernel_public_preflight_gate_filename() -> None:
    assert _GATE.name == "test_post_pmi_kernel_public_contract_preflight_gate.py"


def test_kernel_public_preflight_brief_pass() -> None:
    assert _BRIEF.is_file()
    text = _BRIEF.read_text(encoding="utf-8")
    assert "**Status:** **PASS**" in text or "Status:** **PASS**" in text
    results = text.split("## Results (retry", 1)[1].split("## Question answered", 1)[0]
    for label in (
        "| 1 | Recruitment | **PASS**",
        "| 2 | Employment | **PASS**",
        "| 3 | Boundary | **PASS**",
        "| 4 | Documents | **PASS**",
        "| 5 | Workforce | **PASS**",
        "| **Preflight** | — | **PASS**",
    ):
        assert label in results, label
    assert "dual zero-policy" in text.lower()
    assert "not P1→P6" in text or "not P1->P6" in text or "not an immediate jump to P1" in text


def test_recruitment_public_ready_exposes_selector_and_evaluate() -> None:
    src = _READY_PUBLIC.read_text(encoding="utf-8")
    tree = ast.parse(src)
    exports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "__all__"
                    and isinstance(node.value, (ast.List, ast.Tuple))
                ):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            exports.append(elt.value)
    assert "evaluate_ready_transfer" in exports
    assert "READY_COMPOSITION_ID_KEY" in exports
    assert "COMPOSITION_EMPTY" in exports
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert "recruitment_package_readiness" not in mod
            assert "transfer_policy_resolver" not in mod


def test_cold_import_of_recruitment_public_ready_succeeds() -> None:
    probe = (
        "import importlib\n"
        "m = importlib.import_module('backend.app.modules.recruitment.public.ready')\n"
        "assert m.COMPOSITION_EMPTY == 'empty'\n"
        "r = m.resolve_ready_composition_v1({m.READY_COMPOSITION_ID_KEY: 'empty'})\n"
        "assert r['resolved'] is True and r['capabilities'] == []\n"
        "raise SystemExit(0)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(_REPO_ROOT),
        env={
            **dict(**{k: v for k, v in __import__("os").environ.items()}),
            "PYTHONPATH": f"{_REPO_ROOT}:{_REPO_ROOT / 'backend'}",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_module_local_fix_is_pass() -> None:
    assert _OWNED_FIX.is_file()
    text = _OWNED_FIX.read_text(encoding="utf-8")
    assert "**Status:** **PASS**" in text or "Status:** **PASS**" in text


def test_employment_public_exposes_admit_host_evaluate() -> None:
    m = importlib.import_module("backend.app.modules.employment.public.commands")
    assert "evaluate_start_allowed_for_handoff" in m.__all__
    assert "apply_employment_accept_policy" in m.__all__
    assert "confirm_employment_started_for_handoff" in m.__all__
    assert "resolve_admit_ruleset_v1" not in m.__all__


def test_boundary_public_accepts_rfe_without_recruitment_internals() -> None:
    m = importlib.import_module("backend.app.modules.boundary.public.ready")
    assert "validate_ready_for_employment_package_v1" in m.__all__
    assert m.CONTRACT_ID == "ready_for_employment.v1"
    errs = m.validate_ready_for_employment_package_v1({"not": "rfe"})
    assert isinstance(errs, list) and errs
    src = (
        _REPO_ROOT / "backend" / "app" / "modules" / "boundary" / "public" / "ready.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not (
                node.module.startswith("backend.app.modules.recruitment")
                and ".public" not in node.module
            )


def test_documents_public_evidence_only_no_lifecycle_authority() -> None:
    m = importlib.import_module("backend.app.modules.documents.public.evidence")
    assert len(m.__all__) >= 3
    banned = {
        "transfer_allowed",
        "start_allowed",
        "evaluate_ready_transfer",
        "evaluate_start_allowed_for_handoff",
        "TransferPolicyResolver",
    }
    assert not (banned & set(m.__all__))


def test_workforce_public_started_consumer() -> None:
    m = importlib.import_module("backend.app.modules.workforce.public.started")
    for name in (
        "find_employee_by_candidate",
        "ensure_hr_profiles_bundle",
        "get_work_eligibility_profile",
    ):
        assert name in m.__all__
        assert callable(getattr(m, name))
