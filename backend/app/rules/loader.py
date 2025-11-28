from __future__ import annotations

import os
from functools import lru_cache

import yaml

_RULES_FILE = os.getenv("RULES_FILE", "backend/app/rules/rules.yml")


@lru_cache(maxsize=1)
def get_rules() -> dict:
    try:
        with open(_RULES_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                return {}
            return data
    except FileNotFoundError:
        return {}
