"""Forms Field Catalog P1.1 — version parsing and compatibility (semver).

Compatibility model:
- major — breaking (clients never auto-jump majors)
- minor — backward-compatible within the same major
- patch — fixes without contract change

A candidate satisfies a requested version when:
  candidate.major == requested.major
  AND (candidate.minor, candidate.patch) >= (requested.minor, requested.patch)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.forms_platform.errors import FormsCatalogVersionInvalidError

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"
)


@dataclass(frozen=True, slots=True, order=True)
class ComponentSemver:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @property
    def tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)


def parse_component_version(version: str) -> ComponentSemver:
    raw = str(version or "").strip()
    match = _SEMVER_RE.match(raw)
    if match is None:
        raise FormsCatalogVersionInvalidError(
            details={"component_version": version},
        )
    return ComponentSemver(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
    )


def is_compatible(requested: str | ComponentSemver, candidate: str | ComponentSemver) -> bool:
    """True if candidate may be used when client asked for requested (same major, >=)."""
    req = requested if isinstance(requested, ComponentSemver) else parse_component_version(requested)
    cand = candidate if isinstance(candidate, ComponentSemver) else parse_component_version(candidate)
    if cand.major != req.major:
        return False
    return cand.tuple >= req.tuple


def compare_versions(a: str | ComponentSemver, b: str | ComponentSemver) -> int:
    """Return -1 / 0 / 1 for a < b / a == b / a > b."""
    left = a if isinstance(a, ComponentSemver) else parse_component_version(a)
    right = b if isinstance(b, ComponentSemver) else parse_component_version(b)
    if left.tuple < right.tuple:
        return -1
    if left.tuple > right.tuple:
        return 1
    return 0
