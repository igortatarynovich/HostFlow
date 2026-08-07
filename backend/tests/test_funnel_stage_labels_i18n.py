"""Normalize funnel stage labels_i18n payloads."""

from backend.app.api.v1.funnels import _normalize_labels_i18n


def test_normalize_labels_i18n_keeps_allowed_locales() -> None:
    assert _normalize_labels_i18n(
        {"pl": "Nowy", "ru": " Новый ", "en": "New", "de": "Neu", "xx": ""}
    ) == {"pl": "Nowy", "ru": "Новый", "en": "New"}


def test_normalize_labels_i18n_empty_and_invalid() -> None:
    assert _normalize_labels_i18n(None) is None
    assert _normalize_labels_i18n({}) is None
    assert _normalize_labels_i18n("nope") is None
    assert _normalize_labels_i18n({"pl": "  "}) is None
