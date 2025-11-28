from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    RECRUITER = "recruiter"
    VIEWER = "viewer"
