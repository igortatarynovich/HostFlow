"""Lightweight checks for recruitment team flow seed constants (no DB)."""

from __future__ import annotations

import uuid

from backend.app.db.seeds.recruitment_team_flow_scenario import (
    CANDIDATE_IDS,
    COMPANY_ID,
    DEFAULT_SCENARIO_TENANT_ID,
    EMAILS,
    USER_IDS,
    VACANCY_ID,
    WORKFORCE_IDS,
)


def test_scenario_tenant_id_is_valid_uuid():
    uuid.UUID(DEFAULT_SCENARIO_TENANT_ID)


def test_deterministic_entity_ids_are_stable():
    assert COMPANY_ID == "c6599b33-c59a-515c-8d99-9049c3bfaafe"
    assert VACANCY_ID == "05ae35a6-2dbe-5c7a-8103-9f861167ac41"
    assert len(USER_IDS) == 5
    assert len(CANDIDATE_IDS) == 4
    assert CANDIDATE_IDS["hr_readonly"] == "ccde37f1-618d-5a97-9fa7-aafa562e6fc2"
    assert WORKFORCE_IDS["hr_readonly"] == "de6bd134-5f58-555f-9264-2292c3bb9662"


def test_scenario_emails_are_distinct():
    emails = [EMAILS.admin, EMAILS.supervisor, EMAILS.recruiter_a, EMAILS.recruiter_b, EMAILS.hr]
    assert len(set(emails)) == len(emails)
