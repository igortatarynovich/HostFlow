from __future__ import annotations

from backend.tests.test_support.repo_paths import read_repo_text


def test_no_direct_reference_foundation_imports_in_remediated_consumers() -> None:
    hr_risk = read_repo_text("backend/app/services/hr_operational_risk.py")
    workforce_eligibility = read_repo_text("backend/app/services/workforce_eligibility_resolver.py")

    assert "from backend.app.constants.reference_foundation import" not in hr_risk
    assert "from backend.app.constants.reference_foundation import" not in workforce_eligibility


def test_no_cross_domain_document_imports_in_remediated_consumers() -> None:
    hr_queue = read_repo_text("backend/app/services/hr_documents_queue.py")
    candidate_tg = read_repo_text("backend/app/services/candidate_telegram_notifications.py")

    assert "from backend.app.modules.documents" not in hr_queue
    assert "from backend.app.modules.documents" not in candidate_tg


def test_phase1a_forbidden_scope_imports_not_present() -> None:
    immutable = read_repo_text("backend/app/reference/core_immutable_catalogs.py")
    immutable_seed = read_repo_text("backend/app/reference/core_immutable_catalogs_seed.py")

    forbidden_phase1a_patterns = (
        "backend.app.models.ref_document_type",
        "backend.app.services.document_reference_sync",
        "backend.app.services.workforce_",
        "backend.app.modules.leads",
        "backend.app.api.v1",
    )
    for pattern in forbidden_phase1a_patterns:
        assert pattern not in immutable
        assert pattern not in immutable_seed


def test_phase1b_reference_catalog_files_do_not_pull_runtime_modules() -> None:
    legal_catalog = read_repo_text("backend/app/reference/legal_document_catalogs.py")
    field_schema_registry = read_repo_text("backend/app/reference/reference_field_schema_registry.py")
    workforce_transport_catalog = read_repo_text("backend/app/reference/workforce_transport_catalogs.py")
    tenant_override_foundation = read_repo_text("backend/app/reference/reference_tenant_override_foundation.py")
    rule_pack_foundation = read_repo_text("backend/app/reference/reference_rule_pack_foundation.py")
    seed_manifest = read_repo_text("backend/app/reference/reference_seed_manifest.py")
    assert "backend.app.services." not in legal_catalog
    assert "backend.app.modules." not in legal_catalog
    assert "backend.app.api." not in legal_catalog
    assert "backend.app.services." not in field_schema_registry
    assert "backend.app.modules." not in field_schema_registry
    assert "backend.app.api." not in field_schema_registry
    assert "backend.app.services." not in workforce_transport_catalog
    assert "backend.app.modules." not in workforce_transport_catalog
    assert "backend.app.api." not in workforce_transport_catalog
    assert "backend.app.services." not in tenant_override_foundation
    assert "backend.app.modules." not in tenant_override_foundation
    assert "backend.app.api." not in tenant_override_foundation
    assert "backend.app.services." not in rule_pack_foundation
    assert "backend.app.modules." not in rule_pack_foundation
    assert "backend.app.api." not in rule_pack_foundation
    assert "backend.app.services." not in seed_manifest
    assert "backend.app.modules." not in seed_manifest
    assert "backend.app.api." not in seed_manifest


def test_phase1c_catalogs_do_not_contain_runtime_decision_fields() -> None:
    workforce_transport_catalog = read_repo_text("backend/app/reference/workforce_transport_catalogs.py")
    field_schema_registry = read_repo_text("backend/app/reference/reference_field_schema_registry.py")
    tenant_override_foundation = read_repo_text("backend/app/reference/reference_tenant_override_foundation.py")
    rule_pack_foundation = read_repo_text("backend/app/reference/reference_rule_pack_foundation.py")
    seed_manifest = read_repo_text("backend/app/reference/reference_seed_manifest.py")
    forbidden_runtime_markers = (
        "required_for_position",
        "eligibility",
        "suitability",
        "verification",
        "automation",
        "trigger",
        "merge_override",
        "tenant_settings",
        "workflow",
        "execute",
        "blocking",
        "decision",
    )
    for marker in forbidden_runtime_markers:
        assert marker not in workforce_transport_catalog
        assert marker not in field_schema_registry
        assert marker not in tenant_override_foundation
        assert marker not in rule_pack_foundation

    forbidden_executable_seed_markers = (
        "alembic upgrade",
        "db.execute(",
        "insert into ",
        "seed_runner(",
        "runtime_sync(",
        "consumer_rollout(",
    )
    for marker in forbidden_executable_seed_markers:
        assert marker not in seed_manifest
