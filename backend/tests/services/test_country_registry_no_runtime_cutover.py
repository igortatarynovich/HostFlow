from __future__ import annotations

import inspect

from backend.app.api.v1 import catalogs as catalogs_api
from backend.app.constants import catalogs as runtime_catalogs


def test_r1_does_not_cut_over_runtime_catalogs_sot() -> None:
    """Reference R1 must leave catalogs.py as runtime SoT (cutover is R2)."""
    source = inspect.getsource(catalogs_api)
    assert "backend.app.constants.catalogs import COUNTRIES" in source
    assert "country_registry" not in source
    assert "PL" in runtime_catalogs.COUNTRIES
    assert runtime_catalogs.DIAL_CODES["PL"] == "+48"
    assert runtime_catalogs.DIAL_CODES["XK"] == "+383"
