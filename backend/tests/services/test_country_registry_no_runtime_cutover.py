from __future__ import annotations

import inspect

from backend.app.api.v1 import catalogs as catalogs_api
from backend.app.constants import catalogs as runtime_catalogs
from backend.app.reference.country_registry import (
    ISO_3166_1_ASSIGNED_COUNT,
    get_country_registry_entry,
    list_country_registry_entries,
)


def test_r2_runtime_catalogs_are_registry_projections() -> None:
    """Reference R2: catalogs.py COUNTRIES/DIAL_CODES come from the Country Registry."""
    source = inspect.getsource(catalogs_api)
    assert "backend.app.constants.catalogs import COUNTRIES" in source
    assert "country_registry" not in source

    entries = list_country_registry_entries()
    assert len(runtime_catalogs.COUNTRIES) == ISO_3166_1_ASSIGNED_COUNT
    assert set(runtime_catalogs.COUNTRIES) == {e.identity.alpha2 for e in entries}
    assert set(runtime_catalogs.DIAL_CODES) == set(runtime_catalogs.COUNTRIES)
    assert "XK" not in runtime_catalogs.COUNTRIES
    assert "XK" not in runtime_catalogs.DIAL_CODES
    pl = get_country_registry_entry("PL")
    assert pl is not None
    assert runtime_catalogs.COUNTRIES["PL"] == pl.labels.ru
    assert runtime_catalogs.DIAL_CODES["PL"] == pl.classifications.dial_code == "+48"
    assert runtime_catalogs.DIAL_CODES["US"] == runtime_catalogs.DIAL_CODES["CA"] == "+1"
