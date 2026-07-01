# Integrations Module Dependency Audit

Status: baseline-established  
Date: 2026-05-29

## Audit Scope

1. direct cross-module imports in integration entrypoints;
2. reference/facade bypass for canonical normalization;
3. local duplicate normalization surfaces;
4. temporary exception linkage.

## Verified Boundary Outcomes (REF-4)

Closed blocker-1:
1. direct `backend.app.modules.documents.*` imports removed from integration entrypoints;
2. switched to `document_hub_delivery_contract` adapters.

Closed blocker-2:
1. raw citizenship/country handling remediated through integration-level inbound normalizer backed by `ReferenceServiceFacade`.

Closed blocker-3:
1. duplicate normalization surfaces consolidated for inbound country/citizenship paths in intake/leads/telegram flows.

## Current Findings

Must-fix (current):
1. none in integrations slice gate scope.

Baseline notes:
1. full integrations target pack execution remains a follow-up baseline note in gate/report;
2. no new unknown blocker-class direct-access pattern identified in full-system adoption scan.

## Guard Scan Commands

```bash
cd /opt/HostFlow && rg -n \
  "from backend.app.modules.documents|ReferenceServiceFacade|integration_inbound_normalization|citizenship|country|normalize|webhook|intake" \
  backend/app/api/public/intake.py backend/app/api/v1/communications/_helpers/telegram_intake/*.py backend/app/modules/leads/*.py backend/app/modules/leads/service/*.py
```

```bash
cd /opt/HostFlow && rg -n "EXC-005|EXC-006|EXC-008|EXC-010" docs/specs/gates/system_direct_access_exceptions_registry.md
```
