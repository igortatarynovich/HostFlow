from __future__ import annotations

import inspect

from backend.app.services import hr_handoff_profile_context as mod


def test_load_handoff_profile_namespace_references_snapshot_model() -> None:
  source = inspect.getsource(mod.load_handoff_profile_namespace)
  assert "CandidateHandoffSnapshot" in source
  assert getattr(mod, "CandidateHandoffSnapshot", None) is not None
