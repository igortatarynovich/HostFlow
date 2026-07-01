from backend.app.legal.billing_terms_templates_v1 import (
    ALL_LEGAL_DOC_TYPES,
    BILLING_LEGAL_DOC_TYPES,
    default_billing_template_items,
)


def test_all_types_include_core_and_billing() -> None:
    assert "rodo_clause" in ALL_LEGAL_DOC_TYPES
    assert "privacy_policy" in ALL_LEGAL_DOC_TYPES
    assert BILLING_LEGAL_DOC_TYPES <= ALL_LEGAL_DOC_TYPES
    assert len(BILLING_LEGAL_DOC_TYPES) == 6


def test_default_items_cover_billing_types() -> None:
    items = default_billing_template_items()
    types = {x["type"] for x in items}
    assert types == BILLING_LEGAL_DOC_TYPES
    for x in items:
        assert x["version_id"]
        assert "DRAFT" in (x.get("content_html") or "")
