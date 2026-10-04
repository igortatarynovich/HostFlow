"""Read the Employee Data ownership answer. This module does not list person facts.

Completeness is the answer already given for that set. The fingerprint is
the live owner values, so a later change is visible. No fact is required
or rejected here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class EmployeeDataReading:
    complete: bool
    fingerprint: str


def _fingerprint(facts: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(facts), sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def read_employee_data_set(facts: Mapping[str, Any] | None, *, complete: bool) -> EmployeeDataReading:
    """Return the ownership answer and a fingerprint of the values handed in."""

    return EmployeeDataReading(complete=bool(complete) and complete is True, fingerprint=_fingerprint(facts or {}))
