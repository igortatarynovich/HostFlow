"""Phase 2.6.G-5 Stage F — canonical ``?recruiter_id=`` query param on
candidate list endpoints.

Spec: ``docs/specs/manager-assignment.md`` §4 Stage F.

Before Stage F the candidate list filter was exposed as ``?manager_id=``
only; FE had to keep sending the legacy name even though the canonical
column is ``Candidate.recruiter_id``. Stage F introduces ``?recruiter_id=``
as the canonical query name on both list endpoints (``GET /candidates``
and ``GET /candidates/no-next-action``) while keeping ``?manager_id=`` as
a BC alias for one release cycle.

Scope of this test file:

* **Router param acceptance** — ``?recruiter_id=<uuid>`` is accepted on
  both endpoints without 422 (the router declares the param). A 422
  would bite FE immediately on deploy.
* **Both names funnel to the same internal filter** — verified at the
  handler level using FastAPI's signature (introspecting the resolved
  ``filters["manager"]`` would require a TestClient flow; we instead
  check that both query names are declared and typed as ``UUID``).
* **Response payload schema** — ``CandidateOut`` (Pydantic) now declares
  ``recruiter_id`` / ``recruiter_name`` / ``recruiter_short``; the wire
  payload built by ``_serialize_candidate_row`` already had them, Stage F
  pins them into the schema so OpenAPI/TS types stay truthful.

**NOT covered here** (already covered elsewhere):

* OR-on-both-columns filter behaviour — locked in by
  ``test_candidate_manager_shadow_write.test_repo_manager_filter_matches_recruiter_id_only``
  (Stage D). Stage F wiring funnels into the same ``filters["manager"]``
  key, so the SQL OR is unchanged.
* End-to-end HTTP smoke — the default test tenant is an agency, so
  ``GET /candidates`` intentionally returns empty unless the candidate
  is linked to a client-tenant handoff. That tenancy dance is out of
  scope for this wave.
"""

from __future__ import annotations

import inspect
from typing import get_args, get_origin
from uuid import UUID

import pytest

from backend.app.api.v1.candidates.router import (
    list_candidates,
    list_candidates_no_next_action,
)
from backend.app.api.v1.candidates.schemas import CandidateOut


pytestmark = pytest.mark.anyio


def _param_is_optional_uuid(param: inspect.Parameter) -> bool:
    """Return True for ``UUID | None`` / ``Optional[UUID]`` annotations.

    Handles both ``UUID | None`` (PEP-604) and ``Optional[UUID]``
    because the candidates router mixes both.
    """
    ann = param.annotation
    if ann is UUID:
        return True
    origin = get_origin(ann)
    if origin is None:
        return False
    args = {a for a in get_args(ann) if a is not type(None)}
    return args == {UUID}


def test_list_candidates_declares_recruiter_id_param() -> None:
    """``GET /candidates`` MUST accept ``recruiter_id`` as an Optional
    UUID query parameter (Stage F canon).

    Guards against accidental removal / rename — FE will start sending
    ``?recruiter_id=`` and a 422 would make the UI list unusable.
    """
    sig = inspect.signature(list_candidates)
    assert "recruiter_id" in sig.parameters, (
        "Stage F regressed: ``list_candidates`` no longer accepts "
        "``?recruiter_id=`` — FE Stage F migration will 422."
    )
    assert _param_is_optional_uuid(sig.parameters["recruiter_id"])


def test_list_candidates_still_accepts_manager_id_alias() -> None:
    """Legacy BC alias ``?manager_id=`` MUST keep working for one
    release cycle — Stage G is where we drop it.
    """
    sig = inspect.signature(list_candidates)
    assert "manager_id" in sig.parameters
    assert _param_is_optional_uuid(sig.parameters["manager_id"])


def test_no_next_action_declares_recruiter_id_param() -> None:
    """``GET /candidates/no-next-action`` MUST mirror the main list
    endpoint — both handlers wire their filter state independently, so
    they can drift. This test prevents that.
    """
    sig = inspect.signature(list_candidates_no_next_action)
    assert "recruiter_id" in sig.parameters
    assert _param_is_optional_uuid(sig.parameters["recruiter_id"])
    assert "manager_id" in sig.parameters


def test_candidate_out_schema_exposes_recruiter_triplet() -> None:
    """``CandidateOut`` MUST declare ``recruiter_id`` / ``recruiter_name``
    / ``recruiter_short`` so OpenAPI / generated TypeScript types match
    the actual wire payload built by ``_serialize_candidate_row``.

    Stage F migration on the FE assumes these three fields are declared
    on the DTO — an accidental drop would quietly regress TS typings to
    ``any``.
    """
    fields = CandidateOut.model_fields
    for name in ("recruiter_id", "recruiter_name", "recruiter_short"):
        assert name in fields, (
            f"Stage F regressed: ``CandidateOut`` no longer declares "
            f"``{name}`` — FE generated types will lose it."
        )

    # Sanity: the legacy triplet is still declared (Stage F keeps BC).
    for name in ("manager", "manager_name", "manager_short"):
        assert name in fields, (
            f"``CandidateOut.{name}`` dropped — Stage F keeps BC; "
            f"dropping ``manager`` fields is a Stage G concern."
        )
