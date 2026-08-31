"""Deployed-build identity carried by the running process (OL-2A C-3).

Values come from the image/build environment. They are never read from a
working-tree `.git` at request time — that would re-introduce the bind-mount
lie this module exists to retire.
"""

from __future__ import annotations

import os
from typing import TypedDict


class BuildInfo(TypedDict):
    revision: str
    version: str
    built_at: str


_UNKNOWN = "unknown"


def read_build_info() -> BuildInfo:
    """Return the identity baked into this process at build/start time."""
    revision = (os.getenv("HOSTFLOW_REVISION") or os.getenv("GIT_SHA") or "").strip()
    version = (os.getenv("HOSTFLOW_VERSION") or os.getenv("GIT_REF") or "").strip()
    built_at = (os.getenv("HOSTFLOW_BUILT_AT") or os.getenv("BUILD_TIME") or "").strip()
    return {
        "revision": revision or _UNKNOWN,
        "version": version or _UNKNOWN,
        "built_at": built_at or _UNKNOWN,
    }
