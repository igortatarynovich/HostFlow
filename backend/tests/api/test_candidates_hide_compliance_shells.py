"""Unattached ADR-031 compliance shells must not appear in Candidates lists."""

from __future__ import annotations

from sqlalchemy import and_

from backend.app.api.v1.candidates.repo import (
    _build_conditions,
    unattached_compliance_shell_clause,
)


def test_unattached_compliance_shell_clause_targets_extra_json_text() -> None:
    sql = str(unattached_compliance_shell_clause().compile(compile_kwargs={"literal_binds": True}))
    assert "compliance_candidate_shell_v1" in sql
    assert "compliance_shell_attached_at_process" in sql


def test_candidate_list_conditions_exclude_unattached_shells() -> None:
    sql = str(
        and_(*_build_conditions("11111111-1111-1111-1111-111111111111", {})).compile(
            compile_kwargs={"literal_binds": True}
        )
    )
    assert "compliance_candidate_shell_v1" in sql
    assert "compliance_shell_attached_at_process" in sql
