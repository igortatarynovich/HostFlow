# compat shim — не меняет API
from backend.app.api.v1.candidates.router import router  # noqa: F401
from backend.app.api.v1.candidates.schemas import (      # noqa: F401
    CandidateCreate, CandidateUpdate, CandidateOut
)