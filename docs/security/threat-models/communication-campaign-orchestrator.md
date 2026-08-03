# Threat Model — Communication Campaign Orchestrator (C2.3)

## Assets

- Communication Campaign domain (`communication_campaigns*` tables)  
- Audience snapshot + CampaignRun / RunItem  
- Intent fan-out via existing Communication Intent pipeline  
  (`backend/app/communications/campaign/**` ·  
  `backend/app/api/v1/communications/routes/campaigns.py`)  
- Thin admin UI: Settings → Communications → Campaigns

## Trust boundaries

- Authenticated tenant admin/operator → communications campaign APIs (JWT + `X-Tenant-Id` + RLS)
- Campaign package **must not** call providers, mutate Thread, or write Message/Delivery
- Audience resolution uses caller-supplied entity pool / static list — no cross-module Recruitment/Sales imports
- Distinct from Acquisition `acq_campaigns` Marketing Campaigns

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| CC-1 | Cross-tenant campaign / run leak | Missing tenant scope on list/get/run |
| CC-2 | Privilege to fan-out Intent as another tenant | Spoofed tenant on emit |
| CC-3 | Second send pipeline | Campaign calling providers / Thread writers |
| CC-4 | Audience over-reach | Resolving entities outside tenant / without capability |
| CC-5 | Idempotency bypass / duplicate Intent storm | Replay run without idempotency key |
| CC-6 | Confusion with Acquisition Campaigns | Shared naming / wrong SoT |

## Митигации

- All campaign rows tenant-scoped; HTTP uses same communications auth as templates/automation
- Intent-only egress: emitter uses C2.2 `execute_intent` path; no provider/Thread imports in campaign package
- Capability-isolation contract tests (`test_c2_3_*`)
- Run idempotency key unique per tenant
- Separate tables/routes/UI labels (Communications Campaigns vs Marketing Acquisition)

## Тесты

- `backend/tests/communications/test_c2_3_campaign_domain.py`
- `backend/tests/communications/test_c2_3_campaign_audience_resolver.py`
- `backend/tests/communications/test_c2_3_campaign_emitter.py`
- `backend/tests/communications/test_c2_3_campaign_orchestrator.py`
- `backend/tests/communications/test_c2_3_campaign_api.py`

## Связанные спеки

- [`docs/specs/tasks/c2-3-campaign-orchestrator.md`](../../specs/tasks/c2-3-campaign-orchestrator.md)
- [`docs/security/threat-models/automations.md`](./automations.md)
