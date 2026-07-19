"""ADR-007 Forms platform contract constants (C4 bridge)."""

from __future__ import annotations

FORMS_PLATFORM_CONTRACT_VERSION = "forms_platform_v1"
FORMS_PLATFORM_ADR = "ADR-007"

PUBLICATION_MODE_STANDALONE = "standalone"
PUBLICATION_MODE_LINKED = "linked"

STORAGE_BACKEND_TENANT_LEAD_FORM = "tenant_lead_form"

HANDLER_RECRUITMENT_LEAD_DRAFT = "recruitment.lead_draft"
# Legacy — must NOT be used for sales_inquiry (Runtime Split R2/R3).
HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT = "recruitment.client_lead_draft"
HANDLER_SALES_INQUIRY_DRAFT = "sales.inquiry_draft"

FORMS_TIER_BASIC = "basic"

# Sprint 2 lifecycle / error codes (stable)
LIFECYCLE_DRAFT = "draft"
LIFECYCLE_ACTIVE = "active"
LIFECYCLE_ARCHIVED = "archived"

PUBLIC_CONTRACT_ID = "forms.public_contract.v1"
ADAPTER_ID = "forms.endpoint_adapter_v1"
