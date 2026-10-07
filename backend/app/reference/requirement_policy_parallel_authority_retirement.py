"""RPM-3A parallel authority retirement — shared codes and helpers.

Retires independent “need document X?” writers that are not R5:
document_policies writes, leftover ruleset writes, P3B document_required.
"""

from __future__ import annotations

from typing import Any, Final, NoReturn

from fastapi import HTTPException

REQUIREMENT_POLICY_PATH: Final[str] = "/app/settings/requirement-policy"

DOCUMENT_POLICIES_WRITES_RETIRED: Final[str] = "document_policies_writes_retired"
RULESET_WRITES_RETIRED: Final[str] = "ruleset_authority_writes_retired"
P3B_DOCUMENT_REQUIRED_RETIRED: Final[str] = "p3b_document_required_retired_as_answerer"

CONTRACT_ID: Final[str] = "requirement_policy_parallel_authority_retirement.v1"


def raise_document_policies_writes_retired() -> NoReturn:
    raise HTTPException(
        status_code=410,
        detail={
            "code": DOCUMENT_POLICIES_WRITES_RETIRED,
            "message": (
                "Document policy table writes are retired as requirement authority. "
                "Manage required document types at Settings → Requirement Policy."
            ),
            "requirement_policy_path": REQUIREMENT_POLICY_PATH,
            "contract_id": CONTRACT_ID,
        },
    )


def raise_ruleset_writes_retired() -> NoReturn:
    raise HTTPException(
        status_code=410,
        detail={
            "code": RULESET_WRITES_RETIRED,
            "message": (
                "Ruleset create/activate/rollback is retired as requirement authority. "
                "History remains read-only. Manage required types at Settings → Requirement Policy."
            ),
            "requirement_policy_path": REQUIREMENT_POLICY_PATH,
            "contract_id": CONTRACT_ID,
        },
    )


def raise_p3b_document_required_retired() -> NoReturn:
    raise HTTPException(
        status_code=410,
        detail={
            "code": P3B_DOCUMENT_REQUIRED_RETIRED,
            "message": (
                "P3B document_required overrides no longer answer whether a candidate "
                "must provide document type X. Use Settings → Requirement Policy (R5). "
                "field_required and other P3B rule types remain available."
            ),
            "requirement_policy_path": REQUIREMENT_POLICY_PATH,
            "contract_id": CONTRACT_ID,
        },
    )


def filter_out_document_required_overrides(
    overrides: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Drop P3B document_required rows so they cannot change the required-set."""
    if not overrides:
        return []
    out: list[dict[str, Any]] = []
    for row in overrides:
        if not isinstance(row, dict):
            continue
        rule_type = str(row.get("rule_type") or "").strip().lower()
        if rule_type == "document_required":
            continue
        out.append(row)
    return out
