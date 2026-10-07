"""Storage rules for the Employment persistence slice.

The state function is the backfill. It is not a runtime transition.
Accepted handoff does not create an Employment here.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any, Mapping

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Connection

STATES = ("preparing", "active", "ended")

_ENDED_STATUSES = frozenset({"terminated", "returned", "returned_to_recruitment"})
_ACTIVE_STATUSES = frozenset(
    {
        "active",
        "on_sick_leave",
        "on_vacation",
        "on_leave",
        "suspended",
        "contract_ending",
    }
)

LEGACY_EMPLOYEE_COLUMNS = (
    "hire_date",
    "termination_date",
    "company_id",
    "vacancy_id",
    "recruiter_user_id",
    "handoff_at",
    "handoff_by_user_id",
    "candidate_snapshot",
    "probation_end",
)


def backfill_state(status: str | None, termination_date: date | datetime | None) -> str:
    """One Employment state for an existing employee row.

    ``hire_date`` does not choose the state. ``onboarding`` stays ``preparing``.
    """

    normalized = str(status or "").strip().lower()
    if termination_date is not None or normalized in _ENDED_STATUSES:
        return "ended"
    if normalized in _ACTIVE_STATUSES:
        return "active"
    return "preparing"


def _as_mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def handoff_id_from_meta(meta: Any) -> str | None:
    parsed = _as_mapping(meta)
    if not parsed:
        return None
    raw = str(parsed.get("internal_hr_handoff_id") or "").strip()
    return raw or None


def apply_employment_backfill(bind: Connection) -> None:
    """Insert one Employment per employee and attach every contract card.

    The caller has already created ``hr_employments`` and a nullable
    ``workforce_employments.employment_id``. Legacy employee columns are
    still present. This function does not drop them.
    """

    hr_employments = sa.table(
        "hr_employments",
        sa.column("id"),
        sa.column("tenant_id"),
        sa.column("employee_id"),
        sa.column("state"),
        sa.column("client_company_id"),
        sa.column("started_on"),
        sa.column("ended_on"),
        sa.column("vacancy_id"),
        sa.column("recruiter_user_id"),
        sa.column("handoff_at"),
        sa.column("handoff_by_user_id"),
        sa.column("handoff_id"),
        sa.column("candidate_snapshot", sa.JSON()),
        sa.column("created_at"),
        sa.column("updated_at"),
    )
    now = datetime.now(timezone.utc)
    employees = bind.execute(
        text(
            """
            SELECT id, tenant_id, status, company_id, vacancy_id, recruiter_user_id,
                   hire_date, termination_date, probation_end, handoff_at,
                   handoff_by_user_id, candidate_snapshot, meta
            FROM workforce_employees
            """
        )
    ).mappings()

    for employee in employees:
        employment_id = str(uuid.uuid4())
        state = backfill_state(employee["status"], employee["termination_date"])
        snapshot = _as_mapping(employee["candidate_snapshot"])
        bind.execute(
            hr_employments.insert().values(
                id=employment_id,
                tenant_id=employee["tenant_id"],
                employee_id=employee["id"],
                state=state,
                client_company_id=employee["company_id"],
                started_on=employee["hire_date"],
                ended_on=employee["termination_date"],
                vacancy_id=employee["vacancy_id"],
                recruiter_user_id=employee["recruiter_user_id"],
                handoff_at=employee["handoff_at"],
                handoff_by_user_id=employee["handoff_by_user_id"],
                handoff_id=handoff_id_from_meta(employee["meta"]),
                candidate_snapshot=snapshot,
                created_at=now,
                updated_at=now,
            )
        )
        bind.execute(
            text(
                """
                UPDATE workforce_employments
                SET employment_id = :employment_id
                WHERE employee_id = :employee_id
                  AND (employment_id IS NULL OR employment_id = '')
                """
            ),
            {"employment_id": employment_id, "employee_id": employee["id"]},
        )
        if employee["probation_end"] is not None:
            newest = bind.execute(
                text(
                    """
                    SELECT id, probation_end
                    FROM workforce_employments
                    WHERE employee_id = :employee_id
                    ORDER BY created_at DESC
                    """
                ),
                {"employee_id": employee["id"]},
            ).first()
            if newest is not None and newest.probation_end is None:
                bind.execute(
                    text(
                        """
                        UPDATE workforce_employments
                        SET probation_end = :probation_end
                        WHERE id = :id
                        """
                    ),
                    {"probation_end": employee["probation_end"], "id": newest.id},
                )

    if bind.dialect.name == "postgresql":
        bind.execute(
            text(
                """
                UPDATE workforce_employees
                SET meta = meta - 'internal_hr_handoff_id'
                WHERE meta IS NOT NULL
                  AND meta ? 'internal_hr_handoff_id'
                """
            )
        )
    else:
        bind.execute(
            text(
                """
                UPDATE workforce_employees
                SET meta = json_remove(meta, '$.internal_hr_handoff_id')
                WHERE meta IS NOT NULL
                """
            )
        )


def employment_rows(bind: Connection, employee_id: str) -> list[Mapping[str, Any]]:
    return list(
        bind.execute(
            text(
                """
                SELECT id, employee_id, state, client_company_id, started_on, ended_on,
                       vacancy_id, recruiter_user_id, handoff_id
                FROM hr_employments
                WHERE employee_id = :employee_id
                """
            ),
            {"employee_id": employee_id},
        ).mappings()
    )
