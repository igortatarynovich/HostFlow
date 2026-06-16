from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentApplicabilityDecision:
    work_permit_type: str | None
    visa_required: bool
    driver_attestation_required: bool


def derive_document_applicability_decision(
    *,
    citizenship: str,
    work_country: str,
    role: str,
    eu_countries: set[str],
    oswiadczenie_countries: set[str],
) -> DocumentApplicabilityDecision:
    """
    Module-owned policy for legacy documents applicability behavior.
    Inputs must already be canonical/normalized by caller.
    """
    if citizenship and citizenship not in eu_countries:
        work_permit_type = "oswiadczenie" if citizenship in oswiadczenie_countries else "zezwolenie_A"
    else:
        work_permit_type = None

    visa_required = bool(citizenship and citizenship not in eu_countries and work_country == "PL")
    driver_attestation_required = bool(role == "driver" and citizenship and citizenship not in eu_countries)

    return DocumentApplicabilityDecision(
        work_permit_type=work_permit_type,
        visa_required=visa_required,
        driver_attestation_required=driver_attestation_required,
    )

