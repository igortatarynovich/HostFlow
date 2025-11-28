"""Compatibility layer that re-exports the v1 companies router.

Historically the router lived under ``backend.app.api.v1.companies``; the
domain module now resides in ``backend.app.modules.companies``.  This file
keeps downstream imports stable while delegating all logic to the module
implementation.
"""

from backend.app.modules.companies.router import router  # noqa: F401
from backend.app.modules.companies.schemas import (  # noqa: F401
    CompanyCreate as CompanyIn,
    CompanyOut,
    CompanyUpdate as CompanyPatch,
)

__all__ = ["router", "CompanyIn", "CompanyPatch", "CompanyOut"]
