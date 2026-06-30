"""Process Engine module manifests."""

from backend.app.process_engine.manifests.hr import hr_module_manifest
from backend.app.process_engine.manifests.recruitment import recruitment_module_manifest

__all__ = ["hr_module_manifest", "recruitment_module_manifest"]
