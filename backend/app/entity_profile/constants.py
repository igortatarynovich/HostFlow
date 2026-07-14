"""Entity Profile Definition Registry constants."""

from __future__ import annotations

PLATFORM_TENANT_SCOPE = ""
DEFAULT_REGISTRY_VERSION = "entity_profile_v1"

REGISTRY_STATUS_ACTIVE = "active"
REGISTRY_STATUS_DRAFT = "draft"
REGISTRY_STATUS_ARCHIVED = "archived"

RECRUITMENT_MODULE = "recruitment"
ENTITY_CANDIDATE = "candidate"

SERVICE_SALES_MODULE = "service_sales"
ENTITY_LEAD = "lead"
TARGETED_ADVERTISING_PROFILE_CODE = "service_sales.targeted_advertising"
TARGETED_ADVERTISING_PRESENTATION_CODE = "service_sales.targeted_advertising.public_pl"

DRIVER_CE_PROFILE_CODE = "recruitment.candidate.driver_ce"
DRIVER_CE_INTAKE_PRESENTATION_CODE = "recruitment.candidate.driver_ce.meta_short"

WAREHOUSE_WORKER_PROFILE_CODE = "recruitment.candidate.warehouse_worker"
WAREHOUSE_WORKER_INTAKE_PRESENTATION_CODE = "recruitment.candidate.warehouse_worker.public_short"

DRIVER_CE_UA_PROFILE_CODE = "recruitment.candidate.driver_ce_ua"
DRIVER_CE_UA_INTAKE_PRESENTATION_CODE = "recruitment.candidate.driver_ce_ua.meta_short"

REQUIREMENT_REQUIRED = "required"
REQUIREMENT_OPTIONAL = "optional"
REQUIREMENT_HIDDEN = "hidden"
