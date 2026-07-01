from backend.app.models.vacancy import VacancyStatus, normalize_vacancy_status

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


# Phase 2.6.D Stage D — strict transition matrix for Vacancy.status.
# Mirrors docs/specs/vacancy-statuses.md §5.3. Any update to this map MUST
# also update the spec; the spec is the source of truth for product intent.
VACANCY_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    VacancyStatus.open.value: frozenset(
        {
            VacancyStatus.on_hold.value,
            VacancyStatus.closed.value,
            VacancyStatus.filled.value,
            VacancyStatus.cancelled.value,
        }
    ),
    VacancyStatus.on_hold.value: frozenset(
        {
            VacancyStatus.open.value,
            VacancyStatus.closed.value,
            VacancyStatus.cancelled.value,
        }
    ),
    # Terminal statuses can only be reopened to `open`. Reopen-then-target
    # patterns (e.g. closed -> open -> filled) keep the audit trail honest:
    # callers must explicitly say "I am reopening this", then choose the
    # next state.
    VacancyStatus.closed.value: frozenset({VacancyStatus.open.value}),
    VacancyStatus.filled.value: frozenset({VacancyStatus.open.value}),
    VacancyStatus.cancelled.value: frozenset({VacancyStatus.open.value}),
}


def validate_vacancy_status_transition(cur: object | None, new: object | None) -> None:
    """Strict matrix check for ``Vacancy.status`` PATCH.

    Both inputs are funnelled through :func:`normalize_vacancy_status` first
    so legacy aliases (``paused`` → ``on_hold``) and casing/whitespace noise
    are handled identically to how the writer eventually persists the value.
    Same-status patches are always allowed (idempotent no-op).

    The legacy ``archived`` alias normalises to ``archived`` (passthrough)
    and is rewritten to ``closed`` + ``is_archived=True`` by the service
    layer before this validator runs — see ``VacancyService.patch``.

    Raises:
        ValueError: when the requested transition is not present in
            :data:`VACANCY_ALLOWED_TRANSITIONS`. The vacancies router
            converts this to ``HTTP 409 Conflict`` (state conflict, not
            schema-level malformed input).
    """
    cur_norm = normalize_vacancy_status(cur)
    new_norm = normalize_vacancy_status(new)

    if cur_norm == new_norm:
        return

    allowed = VACANCY_ALLOWED_TRANSITIONS.get(cur_norm)
    if allowed is None:
        # Defensive: ``normalize_vacancy_status`` guarantees a canonical value,
        # so this branch is unreachable today. Keeping it raises loudly if the
        # matrix and the enum ever drift apart instead of silently allowing
        # arbitrary moves.
        raise ValueError(
            f"Vacancy.status has no transitions defined from '{cur_norm}'"
        )
    if new_norm not in allowed:
        raise ValueError(
            f"Vacancy.status transition not allowed: {cur_norm} -> {new_norm}"
        )
