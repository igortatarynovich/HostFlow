"""
API v1 package initializer.

Keep this file minimal: do not import models or DB deps here to avoid
circular imports and double model registration. Routers are imported
directly by `main.py` from their modules (e.g. `app.api.v1.candidates`).
"""

__all__: list[str] = []