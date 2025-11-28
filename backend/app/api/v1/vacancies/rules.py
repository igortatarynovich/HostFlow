ALLOWED_STATUSES = ["new", "interview", "hiring", "employed", "probation", "rejected"]
ALLOWED_TRANSITIONS = {
    "new": {"interview", "rejected"},
    "interview": {"hiring", "rejected"},
    "hiring": {"employed", "rejected"},
    "employed": {"probation"},
}

def validate_status_transition(cur: str, new: str) -> None:
    cur_norm = (cur or "").strip().lower()
    new_norm = (new or "").strip().lower()

    if not cur_norm:
        cur_norm = "new"
    if not new_norm:
        new_norm = cur_norm

    recognised = set(ALLOWED_STATUSES)

    # Если статусы не входят в наш ограниченный список (например, vacancy: open/closed/on_hold),
    # то валидация не применяется.
    if cur_norm not in recognised or new_norm not in recognised:
        return

    if cur_norm in ("probation", "rejected") and new_norm != cur_norm:
        raise ValueError(f"Cannot move from terminal status '{cur}'")
    allowed = ALLOWED_TRANSITIONS.get(cur_norm, set())
    if cur_norm != new_norm and new_norm not in allowed:
        raise ValueError(f"Transition {cur} -> {new} is not allowed")
