"""Forms-owned compatibility matrix (C2).

Closed set of allowed
(manifest_version × public_contract_version × adapter_version) tuples.

Not a platform registry. Not a generic capability framework.
A second consumer would be required before extracting this.
"""

from __future__ import annotations

from typing import NamedTuple

from backend.app.forms_platform.constants import ADAPTER_ID, PUBLIC_CONTRACT_VERSION
from backend.app.forms_platform.errors import FormsIdentityIncompatibleError
from backend.app.forms_platform.manifest import FORMS_MANIFEST_VERSION


class CompatibilityTuple(NamedTuple):
    manifest_version: str
    public_contract_version: str
    adapter_version: str


# Sealed C1 lineage. Additive rows only when a new lineage is declared compatible.
COMPATIBLE_TUPLES: frozenset[CompatibilityTuple] = frozenset(
    {
        CompatibilityTuple(
            manifest_version=FORMS_MANIFEST_VERSION,
            public_contract_version=PUBLIC_CONTRACT_VERSION,
            adapter_version=ADAPTER_ID,
        ),
    }
)


def compatibility_tuple(
    *,
    manifest_version: str,
    public_contract_version: str,
    adapter_version: str,
) -> CompatibilityTuple:
    return CompatibilityTuple(
        manifest_version=str(manifest_version),
        public_contract_version=str(public_contract_version),
        adapter_version=str(adapter_version),
    )


def is_compatible_tuple(
    *,
    manifest_version: str,
    public_contract_version: str,
    adapter_version: str,
) -> bool:
    return compatibility_tuple(
        manifest_version=manifest_version,
        public_contract_version=public_contract_version,
        adapter_version=adapter_version,
    ) in COMPATIBLE_TUPLES


def assert_compatible_tuple(
    *,
    manifest_version: str,
    public_contract_version: str,
    adapter_version: str,
) -> CompatibilityTuple:
    row = compatibility_tuple(
        manifest_version=manifest_version,
        public_contract_version=public_contract_version,
        adapter_version=adapter_version,
    )
    if row not in COMPATIBLE_TUPLES:
        raise FormsIdentityIncompatibleError(
            details={
                "manifest_version": row.manifest_version,
                "public_contract_version": row.public_contract_version,
                "adapter_version": row.adapter_version,
            }
        )
    return row
