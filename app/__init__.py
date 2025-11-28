"""Compatibility shim so imports like ``from app import ...`` resolve to backend modules."""

from __future__ import annotations

import sys
from importlib import import_module

_backend_pkg = import_module("backend")
_backend_app = import_module("backend.app")

# Expose backend.app attributes/modules via this package
globals().update(vars(_backend_app))
__all__ = getattr(_backend_app, "__all__", [])
__path__ = getattr(_backend_app, "__path__", [])

# Provide app.backend alias pointing to the root backend package
sys.modules.setdefault(__name__ + ".backend", _backend_pkg)
