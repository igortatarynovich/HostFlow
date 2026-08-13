"""Forms Platform C1 — Foundation contract seal gates.

Locks contract id, adapter id, and Manifest key set.
Does not require Postgres. P3–P5 stay locked.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.forms_platform.constants import ADAPTER_ID, PUBLIC_CONTRACT_ID
from backend.app.forms_platform.manifest import FORMS_MANIFEST_KEYS, forms_manifest_document

_REPO_ROOT = Path(__file__).resolve().parents[3]

_SEALED_MANIFEST_KEYS = frozenset(
    {
        "forms.general.default_language",
        "forms.general.public_url_base",
        "forms.defaults.tier",
        "forms.defaults.consent_required",
        "forms.policies.consent_version_pin",
        "forms.feature_flags.builder_enabled",
        "forms.feature_flags.themes_advanced",
        "forms.feature_flags.multi_language",
        "forms.limits.max_active_publications",
        "forms.adapter.contract_id",
        "forms.adapter.id",
        "forms.license.advanced_forms",
    }
)

_STALE_BUILDER_UNTIL_P1 = "LOCKED until P1"


def test_c1_contract_and_adapter_ids() -> None:
    assert PUBLIC_CONTRACT_ID == "forms.public_contract.v1"
    assert ADAPTER_ID == "forms.endpoint_adapter_v1"
    doc = forms_manifest_document()
    assert doc["keys"]["forms.adapter.contract_id"]["default"] == PUBLIC_CONTRACT_ID
    assert doc["keys"]["forms.adapter.id"]["default"] == ADAPTER_ID


def test_c1_manifest_key_set_frozen() -> None:
    assert frozenset(FORMS_MANIFEST_KEYS) == _SEALED_MANIFEST_KEYS


def test_c1_docs_drop_builder_locked_until_p1() -> None:
    paths = (
        "docs/specs/architecture/platform-capability-catalog.md",
        "docs/specs/architecture/ADR-007-forms-platform-capability.md",
        "docs/specs/architecture/capability-contract.md",
        "docs/specs/architecture/forms-public-contract.md",
    )
    for rel in paths:
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert _STALE_BUILDER_UNTIL_P1 not in text, rel
        assert "P3" in text and "LOCKED" in text, rel

    catalog = (
        _REPO_ROOT / "docs/specs/architecture/platform-capability-catalog.md"
    ).read_text(encoding="utf-8")
    contract = (
        _REPO_ROOT / "docs/specs/architecture/forms-public-contract.md"
    ).read_text(encoding="utf-8")
    assert PUBLIC_CONTRACT_ID in catalog
    assert ADAPTER_ID in catalog
    assert PUBLIC_CONTRACT_ID in contract
    assert ADAPTER_ID in contract


def test_c1_public_contract_names_phase_c() -> None:
    contract = (
        _REPO_ROOT / "docs/specs/architecture/forms-public-contract.md"
    ).read_text(encoding="utf-8")
    assert "Phase C C1" in contract
    assert "forms-platform-c1-contract-seal.md" in contract
