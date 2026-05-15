"""SQL helpers: candidate still in active recruitment pipeline (stage **or** row status)."""

from __future__ import annotations

from sqlalchemy import func, not_, or_

from backend.app.constants.stages import PIPELINE_COMPLETED_STAGE_CODES

_COMPLETED_TUPLE = tuple(PIPELINE_COMPLETED_STAGE_CODES)


def sql_candidate_active_operational_pipeline(stage_column, status_column):
    """True when neither normalized ``stage`` nor ``status`` is in ``PIPELINE_COMPLETED_STAGE_CODES``."""
    st = func.lower(func.coalesce(stage_column, ""))
    row = func.lower(func.coalesce(status_column, ""))
    return not_(or_(st.in_(_COMPLETED_TUPLE), row.in_(_COMPLETED_TUPLE)))
