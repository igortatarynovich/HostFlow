"""Employee service facade — full proxy of workforce_employees for neighbours."""

from __future__ import annotations

from typing import Any

__all__: list[str] = []  # dynamic proxy


def __getattr__(name: str) -> Any:
    import importlib

    return getattr(importlib.import_module("backend.app.services.workforce_employees"), name)


def __dir__() -> list[str]:
    import importlib

    mod = importlib.import_module("backend.app.services.workforce_employees")
    return sorted(x for x in dir(mod) if not x.startswith("__"))
