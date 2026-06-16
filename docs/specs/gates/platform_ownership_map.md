# Platform Ownership Map

Status: canonical platform navigation map  
Date: 2026-05-29

Related:
- `docs/specs/gates/ref4_phase1_canonical_catalog_architecture.md`
- `docs/specs/gates/ref4_phase2_final_closeout.md`
- `docs/specs/gates/system_layers_information_flow_audit.md`
- `docs/specs/gates/system_direct_access_exceptions_registry.md`

## Purpose

Single source map for platform ownership boundaries:
1. who owns each platform domain;
2. where source of truth lives;
3. which modules consume domain outputs;
4. which contract is the only allowed delivery path.

Hard rule:
1. module runtime logic is not source of truth for platform domains;
2. cross-module consumption must go through listed contracts.

## Ownership Matrix

| Domain | Owner | Source of Truth | Consumers | Contract |
|---|---|---|---|---|
| Countries | Platform Reference | `backend/app/reference/core_immutable_catalogs.py` | HR, Recruitment, Workforce, Documents, Integrations | `ReferenceServiceFacade` + `integration_inbound_normalization.py` |
| Citizenships | Platform Reference | `backend/app/reference/legal_document_catalogs.py` | HR, Recruitment, Workforce, Documents, Integrations | `ReferenceServiceFacade` + `integration_inbound_normalization.py` |
| Documents | Platform Reference + Document Hub | canonical reference catalogs + document hub contract adapters | Documents, HR, Recruitment, Workforce, Integrations | `document_hub_delivery_contract.py` + `ReferenceServiceFacade` |
| Legal Statuses | Platform Reference / Policy Reference | `backend/app/reference/legal_document_catalogs.py` + applicability resolver contracts | HR, Documents, Workforce, Recruitment | `ReferenceServiceFacade.get_applicable_documents(...)` |
| Workforce | Platform Reference + Workforce Domain | `backend/app/reference/workforce_transport_catalogs.py` | Workforce, HR, Recruitment, Integrations | `ReferenceServiceFacade` + `workforce_eligibility_delivery_contract.py` |
| Field Schemas | Platform Reference | `backend/app/reference/reference_field_schema_registry.py` | HR, Recruitment, Workforce, Documents, Integrations | `ReferenceServiceFacade.get_reference_field_schema_snapshot()` |
| Tenant Overrides | Platform/Core Config | `backend/app/reference/reference_tenant_override_foundation.py` | HR, Recruitment, Workforce, Documents, Integrations | `ReferenceServiceFacade.get_tenant_override_foundation_snapshot()` |
| Rule Packs | Policy Reference | `backend/app/reference/reference_rule_pack_foundation.py` | Documents, HR, Workforce, Recruitment | `ReferenceServiceFacade.get_rule_pack_foundation_snapshot()` |
| Integrations | Integration Intake Layer | integration adapters + inbound normalizer + intake/leads contracts | Recruitment, HR, Workforce, Documents | `integration_inbound_normalization.py` + module/API delivery contracts |

## Enforcement Notes

1. promotion to platform layer is allowed only under two-module rule or mandatory cross-module contract;
2. any deviation must be registered in `system_direct_access_exceptions_registry.md`;
3. unresolved `STOP` conditions block next gate progression.
