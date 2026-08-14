"""Forms Platform C4 — Form Runtime (read-only).

Publication (Adapter resolve) → Runtime Model. Not an engine.
Does not import Builder, look up publications, publish, or submit.
"""

from __future__ import annotations

from backend.app.forms_platform.runtime.model import RUNTIME_MODEL_CONTRACT, RuntimeModel
from backend.app.forms_platform.runtime.serve import serve

__all__ = [
    "RUNTIME_MODEL_CONTRACT",
    "RuntimeModel",
    "serve",
]
