"""Workspace Capability Host Contract (typed catalogs + contribution fields).

The platform is the kit (data types → fields → primitives → widgets → tables)
plus the capability / contribution host contract.
The renderer registry is technical lookup only.
"""

from backend.app.platform.workspace_capability.capability import (
    WORKSPACE_CAPABILITY_DEFINITIONS,
    assert_no_rodo_capability_id,
)
from backend.app.platform.workspace_capability.catalogs import (
    MODULE_CONTRIBUTION_IDS,
    PLATFORM_SURFACE_IDS,
    SHARED_CAPABILITY_IDS,
    SHELL_PRIMITIVE_IDS,
    WORKSPACE_CAPABILITY_CLASS_IDS,
)
from backend.app.platform.workspace_capability.contribution import (
    REFERENCE_FIELD_CANONS,
    WORKSPACE_CONTRIBUTION_FIELD_KEYS,
    WORKSPACE_LICENSE_VIEWS,
)
from backend.app.platform.workspace_capability.hosts import (
    APPLICATION_WORKSPACE_HOST,
    ENTITY_WORKSPACE_HOST,
    WORKSPACE_CAPABILITY_HOST_IDS,
    WORKSPACE_HOST_REGION_IDS,
)
from backend.app.platform.workspace_capability.kit import (
    KIT_DATA_TYPE_IDS,
    KIT_FIELD_SOT,
    KIT_LAYER_ORDER,
    KIT_TABLE_FRAME_IDS,
    KIT_TABLE_SOT,
    KIT_UI_PRIMITIVE_IDS,
    KIT_WIDGET_CLASS_IDS,
    KIT_WIDGET_GAP_IDS,
)
from backend.app.platform.workspace_capability.proof import (
    PROOF_CONSUMER_ID,
    PROOF_HOST_ID,
    RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS,
)
from backend.app.platform.workspace_capability.registry import (
    WORKSPACE_RENDERER_REGISTRY,
    WORKSPACE_RENDERER_REGISTRATION_KEYS,
)

__all__ = [
    "APPLICATION_WORKSPACE_HOST",
    "ENTITY_WORKSPACE_HOST",
    "KIT_DATA_TYPE_IDS",
    "KIT_FIELD_SOT",
    "KIT_LAYER_ORDER",
    "KIT_TABLE_FRAME_IDS",
    "KIT_TABLE_SOT",
    "KIT_UI_PRIMITIVE_IDS",
    "KIT_WIDGET_CLASS_IDS",
    "KIT_WIDGET_GAP_IDS",
    "MODULE_CONTRIBUTION_IDS",
    "PLATFORM_SURFACE_IDS",
    "PROOF_CONSUMER_ID",
    "PROOF_HOST_ID",
    "RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS",
    "REFERENCE_FIELD_CANONS",
    "SHARED_CAPABILITY_IDS",
    "SHELL_PRIMITIVE_IDS",
    "WORKSPACE_CAPABILITY_CLASS_IDS",
    "WORKSPACE_CAPABILITY_DEFINITIONS",
    "WORKSPACE_CAPABILITY_HOST_IDS",
    "WORKSPACE_CONTRIBUTION_FIELD_KEYS",
    "WORKSPACE_HOST_REGION_IDS",
    "WORKSPACE_LICENSE_VIEWS",
    "WORKSPACE_RENDERER_REGISTRY",
    "WORKSPACE_RENDERER_REGISTRATION_KEYS",
    "assert_no_rodo_capability_id",
]
