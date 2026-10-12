"""One Candidate.stage change produces one CandidateStageHistory row.

``update_candidate`` writes the column with a Core UPDATE and then inserts
history. Other modules can still assign the mapped attribute, and one reminder
path used to issue its own Core UPDATE. Those writes never reached the history
insert.

``transition_candidate_stage`` is the ORM path: it changes the attribute and
inserts history through the same ``_make_stage_history`` helper. A session
``before_flush`` hook records a row when some later caller assigns ``stage``
directly, and it does not add a second row when history is already pending.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import NO_VALUE

UNSCOPED_STAGE_ASSIGNMENT_REASON = "stage_assigned_outside_transition"
_INSTALLED = False
_make_stage_history = None


def transition_candidate_stage(
    db,
    candidate,
    to_code: str,
    *,
    actor_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> bool:
    """Set ``candidate.stage`` and append one history row when the code changes."""
    from backend.app.api.v1.candidates.service import _make_stage_history

    new_code = str(to_code or "").strip()
    if not new_code:
        return False
    old_code = str(getattr(candidate, "stage", None) or "").strip() or None
    if old_code == new_code:
        return False
    candidate.stage = new_code
    tenant_id = str(getattr(candidate, "tenant_id", None) or "").strip()
    candidate_id = str(getattr(candidate, "id", None) or "").strip()
    if not tenant_id or not candidate_id:
        return True
    db.add(
        _make_stage_history(
            tenant_id,
            candidate_id,
            from_code=old_code,
            to_code=new_code,
            actor_id=actor_id,
            reason=reason,
        )
    )
    return True


def _pending_history_covers(session: Session, candidate_id: str, to_code: str) -> bool:
    from backend.app.models.candidate_stage_history import CandidateStageHistory

    for obj in session.new:
        if not isinstance(obj, CandidateStageHistory):
            continue
        if str(obj.candidate_id) == candidate_id and str(obj.to_code) == to_code:
            return True
    return False


def _record_unscoped_stage_changes(session: Session, flush_context, instances) -> None:
    from backend.app.models.candidate import Candidate

    del flush_context, instances
    factory = _make_stage_history
    if factory is None:
        return
    for candidate in list(session.dirty):
        if not isinstance(candidate, Candidate):
            continue
        if candidate in session.new:
            continue
        state = inspect(candidate)
        if state.pending or state.transient:
            continue
        # Read only in-memory values. Expired attributes must not lazy-load here.
        current = state.dict.get("stage", NO_VALUE)
        if current is NO_VALUE:
            continue
        previous = state.committed_state.get("stage", NO_VALUE)
        if previous is NO_VALUE or previous == current:
            continue
        new_code = str(current or "").strip()
        if not new_code:
            continue
        old_code = str(previous).strip() if previous else None
        if old_code == new_code:
            continue
        identity = state.identity
        if not identity:
            continue
        candidate_id = str(identity[0] or "").strip()
        tenant_raw = state.dict.get("tenant_id", state.committed_state.get("tenant_id", None))
        tenant_id = str(tenant_raw or "").strip()
        if not candidate_id or not tenant_id:
            continue
        if _pending_history_covers(session, candidate_id, new_code):
            continue
        session.add(
            factory(
                tenant_id,
                candidate_id,
                from_code=old_code,
                to_code=new_code,
                actor_id="system",
                reason=UNSCOPED_STAGE_ASSIGNMENT_REASON,
            )
        )


def install_candidate_stage_history_integrity() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    # Import the history helper at registration time, not inside before_flush.
    global _make_stage_history
    from backend.app.api.v1.candidates.service import _make_stage_history as factory

    _make_stage_history = factory
    event.listen(Session, "before_flush", _record_unscoped_stage_changes)
    _INSTALLED = True
