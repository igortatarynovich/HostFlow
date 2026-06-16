# backend/app/constants/__init__.py

from . import spa_paths
from .catalogs import COUNTRIES, DIAL_CODES, LANGUAGES, LANGUAGES_EU
from .reference_foundation import (
    DOMAIN_REGISTRY,
    REFERENCE_DOMAINS,
    RISK_SEVERITY_DICTIONARY,
    get_reference_domain,
    validate_reference_code,
)

__all__ = [
    "COUNTRIES",
    "LANGUAGES",
    "LANGUAGES_EU",
    "DIAL_CODES",
    "REFERENCE_DOMAINS",
    "DOMAIN_REGISTRY",
    "RISK_SEVERITY_DICTIONARY",
    "get_reference_domain",
    "validate_reference_code",
    "spa_paths",
]
