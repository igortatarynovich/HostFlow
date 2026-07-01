"""Rules for work eligibility — document order, fee gates, ZUS gating (PR-4+, transport-focused)."""

from __future__ import annotations

from typing import Any, Optional, Sequence

# Eligibility lifecycle (WorkEligibilityProfile.eligibility_status)
ZUS_REGISTRATION_ALLOWED_STATUSES = frozenset({"ready_for_zus", "eligible_to_work"})
ZUS_REGISTRATION_BLOCKED_STATUSES = frozenset(
    {
        "missing_legal_stay",
        "work_permit_required",
        "work_permit_pending",
        "blocked",
    }
)

REQUIREMENT_WORK_PERMIT_FEE = "work_permit_fee"
REQUIREMENT_RED_PAPER_FEE = "red_paper_fee"

WORK_PERMIT_SUBMITTED_STATUSES = frozenset({"submitted", "lodged", "filed"})
RED_PAPER_ORDER_STATUSES = frozenset({"ordered", "application_submitted", "submitted"})
ELIGIBILITY_REQUIRES_FEES_PAID = frozenset({"ready_for_zus", "eligible_to_work"})

# EU + EEA + CH (ISO 3166-1 alpha-2) — default for free movement vs third-country drivers.
_EU_EEA_CH = frozenset(
    "AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE "
    "IS LI NO CH".split()
)


def _is_third_country(citizenship: Optional[str]) -> bool:
    c = (citizenship or "").strip().upper()
    if len(c) != 2:
        return False
    return c not in _EU_EEA_CH


def foreign_driver_work_permit_path_incomplete(wel: Any) -> bool:
    """Heuristic v1: driver + third-country citizenship + no received work permit date."""
    if (wel.position_category or "").strip().lower() != "driver":
        return False
    if not _is_third_country(wel.citizenship):
        return False
    if wel.work_permit_received_at is not None:
        return False
    if wel.requires_work_permit is False:
        return False
    return True


def foreign_driver_fee_rows_expected(wel: Any) -> bool:
    """When true, we seed / enforce fee payment rows for this profile."""
    if (wel.position_category or "").strip().lower() != "driver":
        return False
    if not _is_third_country(wel.citizenship):
        return False
    if wel.requires_work_permit is False:
        return False
    return True


def payment_row_satisfied(row: Any) -> bool:
    st = (getattr(row, "payment_status", None) or "").strip().lower()
    return st in {"paid", "waived", "not_required"}


def work_permit_fee_paid(payments: Sequence[Any]) -> bool:
    for r in payments:
        if (getattr(r, "requirement_type", None) or "").strip().lower() == REQUIREMENT_WORK_PERMIT_FEE:
            return payment_row_satisfied(r)
    return True


def red_paper_fee_paid(payments: Sequence[Any]) -> bool:
    for r in payments:
        if (getattr(r, "requirement_type", None) or "").strip().lower() == REQUIREMENT_RED_PAPER_FEE:
            return payment_row_satisfied(r)
    return True


def zus_payment_blockers(payments: Sequence[Any]) -> list[str]:
    out: list[str] = []
    for r in payments:
        rt = (getattr(r, "requirement_type", None) or "").strip().lower()
        if rt not in {REQUIREMENT_WORK_PERMIT_FEE, REQUIREMENT_RED_PAPER_FEE}:
            continue
        if (getattr(r, "payment_status", None) or "").strip().lower() == "required" and not payment_row_satisfied(r):
            if rt == REQUIREMENT_WORK_PERMIT_FEE:
                out.append("work_permit_fee")
            elif rt == REQUIREMENT_RED_PAPER_FEE:
                out.append("red_paper_fee")
    return out


def _dedupe_blockers(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        k = str(x).strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def evaluate_zus_registration_gate(
    wel: Optional[Any],
    emp: Any,
    payments: Optional[Sequence[Any]] = None,
) -> tuple[str, list[str]]:
    """
    Returns (mode, blocked_by) where mode is 'allow' or 'blocked'.
    blocked_by lists dependency keys for HR (work_permit, legal_stay, red_paper, work_permit_fee, ...).
    """
    del emp  # reserved for contract / employer-country rules in later phases
    pay = list(payments or [])
    if wel is None:
        return "allow", []

    blockers: list[str] = []
    st = (wel.eligibility_status or "").strip().lower()

    if st in ZUS_REGISTRATION_ALLOWED_STATUSES:
        blockers.extend(zus_payment_blockers(pay))
        if not blockers:
            return "allow", []
        return "blocked", _dedupe_blockers(blockers)

    if st in ZUS_REGISTRATION_BLOCKED_STATUSES:
        if st == "missing_legal_stay":
            blockers.append("legal_stay")
        elif st in ("work_permit_required", "work_permit_pending"):
            blockers.append("work_permit")
        elif st == "blocked":
            blockers.extend(["work_permit", "legal_stay", "red_paper"])
        else:
            blockers.append(st)

    elif st == "not_evaluated":
        if foreign_driver_work_permit_path_incomplete(wel):
            blockers.extend(["legal_stay", "work_permit"])
    else:
        blockers.append(st)

    blockers.extend(zus_payment_blockers(pay))
    if not blockers:
        return "allow", []
    return "blocked", _dedupe_blockers(blockers)


def submission_channel_query_filters(
    *,
    country: str,
    permit_type: Optional[str],
    voivodeship: Optional[str] = None,
) -> dict[str, Optional[str]]:
    """Shape for listing `work_permit_submission_channels` (when HR UI reads DB)."""
    return {
        "country": (country or "").strip().upper()[:8] or None,
        "permit_type": (permit_type or "").strip()[:64] or None,
        "voivodeship": (voivodeship or "").strip()[:64] or None,
    }


def validate_work_eligibility_profile_patch(
    current: Any,
    patch: dict[str, Any],
    payments: Sequence[Any],
) -> None:
    """Raise ValueError when patch violates fee / ordering rules."""

    def _eff(name: str) -> Any:
        if name in patch:
            return patch[name]
        return getattr(current, name, None)

    new_app_status = _eff("work_permit_application_status")
    if new_app_status is not None:
        s = str(new_app_status).strip().lower()
        if s in WORK_PERMIT_SUBMITTED_STATUSES and not work_permit_fee_paid(payments):
            raise ValueError(
                "Work permit fee must be paid (or waived / not required) before marking the application as submitted."
            )

    if patch.get("work_permit_submitted_at") is not None and not work_permit_fee_paid(payments):
        raise ValueError(
            "Work permit fee must be paid (or waived / not required) before setting work permit submitted date."
        )

    new_rp = patch.get("red_paper_status")
    if new_rp is not None:
        s = str(new_rp).strip().lower()
        if s in RED_PAPER_ORDER_STATUSES and not red_paper_fee_paid(payments):
            raise ValueError(
                "Red paper fee must be paid (or waived / not required) before ordering / submitting red paper."
            )

    new_elig = patch.get("eligibility_status")
    if new_elig is not None:
        s = str(new_elig).strip().lower()
        if s in ELIGIBILITY_REQUIRES_FEES_PAID:
            if not work_permit_fee_paid(payments) or not red_paper_fee_paid(payments):
                raise ValueError(
                    "Work permit and red paper fee rows must be paid, waived, or marked not required "
                    "before eligibility can move to this status."
                )
