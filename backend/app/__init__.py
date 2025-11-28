"""Compatibility init so both `import app` and `import backend.app` work.

In some entry points (e.g. `make up`) PYTHONPATH is set to `backend/`, so the
package is available simply as `app`. In others (tests, docker) the project
root is on PYTHONPATH and callers import `backend.app`.  We normalise both
scenarios by registering aliases in ``sys.modules`` without importing the same
package twice.
"""

from __future__ import annotations

import importlib
import sys as _sys
from types import ModuleType

_module: ModuleType

# Try the fully-qualified path first; fall back to the current package when the
# PYTHONPATH already points at backend/.
try:  # pragma: no cover - depends on runtime PYTHONPATH
    _module = importlib.import_module("backend.app")
except ModuleNotFoundError:  # pragma: no cover - dev server path
    _module = _sys.modules.get(__name__, ModuleType(__name__))

# Ensure both spellings resolve to the same module object.
app_module = _sys.modules.setdefault("app", _module)

if "backend" not in _sys.modules:  # pragma: no cover - path dependent
    backend_pkg = ModuleType("backend")
    try:
        backend_pkg.__path__ = list(getattr(_module, "__path__", []))  # type: ignore[attr-defined]
    except Exception:
        backend_pkg.__path__ = []  # pragma: no cover
    def _backend_getattr(name: str):
        if name == "app":
            return _module
        submod = importlib.import_module(f"app.{name}")
        _sys.modules.setdefault(f"backend.{name}", submod)
        return submod
    backend_pkg.__getattr__ = _backend_getattr  # type: ignore[attr-defined]
    backend_pkg.app = _module  # type: ignore[attr-defined]
    _sys.modules["backend"] = backend_pkg

_sys.modules.setdefault("backend.app", _module)
_sys.modules.setdefault("app.backend", _module)
if not hasattr(app_module, "backend"):
    setattr(app_module, "backend", _module)
