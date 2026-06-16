from __future__ import annotations

from backend.app.reference.legal_document_catalogs import (
    CATALOG_VERSION,
    get_citizenship_by_alpha2,
    get_document_type_by_code,
    list_citizenships_canonical,
    list_document_categories_canonical,
    list_document_types_canonical,
    list_legal_statuses_canonical,
    list_permit_types_canonical,
    list_visa_types_canonical,
)


def test_legal_document_catalogs_baseline_shape() -> None:
    assert CATALOG_VERSION.startswith("ref4-phase1b-legal-document-")
    assert len(list_citizenships_canonical()) >= 1
    assert len(list_legal_statuses_canonical()) >= 1
    assert len(list_permit_types_canonical()) >= 1
    assert len(list_visa_types_canonical()) >= 1
    assert len(list_document_categories_canonical()) >= 1
    assert len(list_document_types_canonical()) >= 1


def test_legal_document_catalogs_resolvers() -> None:
    citizenship = get_citizenship_by_alpha2("pl")
    assert citizenship is not None
    assert citizenship.code_alpha2 == "PL"

    passport = get_document_type_by_code("Passport")
    assert passport is not None
    assert passport.code == "passport"
    assert passport.category_code == "identity"
