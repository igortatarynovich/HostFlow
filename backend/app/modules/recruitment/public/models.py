"""Published Recruitment entity types (read surface).

Spine neighbours may depend on these ORM types through this module only.
"""

from __future__ import annotations

from backend.app.models.candidate import Candidate
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.models.vacancy import Vacancy

__all__ = [
    "Candidate",
    "Funnel",
    "FunnelStage",
    "RecruitmentApplication",
    "Vacancy",
]
