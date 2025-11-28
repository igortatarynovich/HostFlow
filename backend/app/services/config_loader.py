from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict

CONFIG_DIR = os.environ.get("HF_CONFIG_DIR", "backend/config")


def _load(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=64)
def load_config(name: str) -> Dict[str, Any]:
    """
    Кэшируем чтение JSON конфигов из backend/config/*.json
    """
    path = os.path.join(CONFIG_DIR, name)
    return _load(path)


def bust_cache() -> None:
    load_config.cache_clear()
