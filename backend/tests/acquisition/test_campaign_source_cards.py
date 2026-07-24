"""Unit tests for Campaign Source card composition (Acquisition PR2)."""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.acquisition.campaign_source_cards import (
    enrich_form_card,
    enrich_intake_source_card,
    form_publication_status,
    humanize_meta_profile_name,
    parse_meta_page_id,
)
from backend.app.acquisition.sources_read import parse_meta_form_id


def test_parse_meta_keys() -> None:
    assert parse_meta_form_id("form_id:1917672235588961") == "1917672235588961"
    assert parse_meta_page_id("page_id:12345") == "12345"
    assert parse_meta_page_id("") is None


def test_humanize_drops_technical_meta_form_placeholder() -> None:
    assert humanize_meta_profile_name("Meta form 1917672235588961", form_id="1917672235588961") is None
    assert humanize_meta_profile_name("Drivers PL", form_id="1917672235588961") == "Drivers PL"


def test_form_publication_status() -> None:
    assert form_publication_status(is_active=False, public_slug="drivers") == "inactive"
    assert form_publication_status(is_active=True, public_slug="drivers") == "published"
    assert form_publication_status(is_active=True, public_slug=None) == "draft"


def test_enrich_form_card_public() -> None:
    form = SimpleNamespace(
        is_active=True,
        public_slug="drivers",
        published_at=None,
    )
    card = enrich_form_card(form, last_submission_at=None)
    assert card.is_public is True
    assert card.publication_status == "published"
    assert card.form_is_active is True


def test_enrich_intake_prefers_meta_form_name() -> None:
    profile = SimpleNamespace(is_active=True, name="Meta form 99", code="meta-form-99")
    binding = SimpleNamespace(
        is_active=True,
        external_key="form_id:99",
        external_key_secondary="page_id:page-1",
        label="Meta form 99",
    )
    meta_map = SimpleNamespace(form_id="99", form_name="Drivers PL", page_id="page-1")
    card = enrich_intake_source_card(
        profile,
        [binding],
        meta_map=meta_map,
        last_submission_at=None,
    )
    assert card.lead_form_name == "Drivers PL"
    assert card.display_title == "Drivers PL"
    assert card.page_id == "page-1"
    assert card.page_name is None
    assert card.meta_form_id == "99"
    assert card.binding_status == "bound"
