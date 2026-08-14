"""Forms Platform C3 — Builder session state machine (contract, not UI).

States describe FormDefinition ↔ Draft only. Publication / Adapter are out of scope.
"""

from __future__ import annotations

from backend.app.forms_platform.errors import FormsBuilderStateError

STATE_NEW = "new"
STATE_DIRTY = "dirty"
STATE_SAVING = "saving"
STATE_SAVED = "saved"
STATE_VALIDATION_ERROR = "validation_error"
STATE_CONFLICT = "conflict"
STATE_CLOSED = "closed"

BUILDER_STATES = frozenset(
    {
        STATE_NEW,
        STATE_DIRTY,
        STATE_SAVING,
        STATE_SAVED,
        STATE_VALIDATION_ERROR,
        STATE_CONFLICT,
        STATE_CLOSED,
    }
)

# Dirty Draft and Saved Draft are both mutable. Publication Version is not a Builder state.
MUTABLE_DRAFT_STATES = frozenset({STATE_NEW, STATE_DIRTY, STATE_SAVED, STATE_VALIDATION_ERROR, STATE_CONFLICT})

EVENT_EDIT = "edit"
EVENT_BEGIN_SAVE = "begin_save"
EVENT_SAVE_OK = "save_ok"
EVENT_SAVE_VALIDATION_ERROR = "save_validation_error"
EVENT_SAVE_CONFLICT = "save_conflict"
EVENT_CLOSE = "close"

_TRANSITIONS: dict[str, dict[str, str]] = {
    EVENT_EDIT: {
        STATE_NEW: STATE_DIRTY,
        STATE_DIRTY: STATE_DIRTY,
        STATE_SAVED: STATE_DIRTY,
        STATE_VALIDATION_ERROR: STATE_DIRTY,
        STATE_CONFLICT: STATE_DIRTY,
    },
    EVENT_BEGIN_SAVE: {
        STATE_NEW: STATE_SAVING,
        STATE_DIRTY: STATE_SAVING,
        STATE_SAVED: STATE_SAVING,
    },
    EVENT_SAVE_OK: {
        STATE_SAVING: STATE_SAVED,
    },
    EVENT_SAVE_VALIDATION_ERROR: {
        STATE_SAVING: STATE_VALIDATION_ERROR,
    },
    EVENT_SAVE_CONFLICT: {
        STATE_SAVING: STATE_CONFLICT,
    },
    EVENT_CLOSE: {
        STATE_NEW: STATE_CLOSED,
        STATE_DIRTY: STATE_CLOSED,
        STATE_SAVED: STATE_CLOSED,
        STATE_VALIDATION_ERROR: STATE_CLOSED,
        STATE_CONFLICT: STATE_CLOSED,
    },
}


def transition(state: str, event: str) -> str:
    current = str(state or "").strip()
    ev = str(event or "").strip()
    allowed = _TRANSITIONS.get(ev)
    if not allowed or current not in allowed:
        raise FormsBuilderStateError(
            details={"from": current, "event": ev, "allowed_from": sorted(allowed or ())},
        )
    nxt = allowed[current]
    if nxt not in BUILDER_STATES:
        raise FormsBuilderStateError(details={"from": current, "event": ev, "to": nxt})
    return nxt
