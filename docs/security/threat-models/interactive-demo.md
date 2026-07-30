# Threat Model — Interactive Demo (Growth)

## Scope

Growth “try HostFlow” surface (`/demo`) and in-tenant **onboarding demo seed** (`POST /onboarding/demo/seed`, `POST /onboarding/clear-demo-data`).

Canon: [`self-service-success-path.md`](../../specs/journeys/self-service-success-path.md) (Demo Wave-1). Architecture funnel: [ADR-034](../../specs/architecture/ADR-034-self-service-public-funnels.md).

## Assets

- Tenant CRM data created by demo seed (sample leads, candidates, companies, reminders).
- Authenticated administrator session that can seed/clear.
- Public marketing copy on `/demo` (no live CRM data).

## Trust boundaries

| Zone | Who |
|------|-----|
| Public Growth | Anonymous visitors on `/demo` |
| Tenant shell | Authenticated users; seed/clear = **administrator** only |
| Shared anonymous demo tenant | **Out of scope for Wave-1** |

## Decision (Wave-1)

**Allowed:** each buyer creates their own workspace via `/signup`, then loads a **tenant-scoped** sample pack and clears it with one API.

**Forbidden until a later gate:** a shared public login / guest tenant that many visitors mutate (requires dedicated isolation, scheduled reset, abuse controls, and CLASS-data guarantees).

## Threats

| ID | Threat | Vector |
|----|--------|--------|
| ID-1 | Cross-tenant leakage via shared demo | Shared guest credentials or fixed demo tenant_id |
| ID-2 | Demo seed pollution of production data | Seed without clear / without `onboarding_demo` tagging |
| ID-3 | Privilege escalation | Non-admin calling seed/clear |
| ID-4 | Abuse / cost | Automated signup + repeated seed |
| ID-5 | PII confusion | Visitors mistaking sample people for real applicants |

## Mitigations (baseline)

- No anonymous shared tenant in Wave-1; `/demo` only explains the path and CTAs → `/signup` / `/login`.
- Seed/clear require `Role.administrator` and operate inside `app.tenant_id` RLS.
- Seeded rows tagged / clearable via `clear_onboarding_demo_data` (existing service).
- Sample pack content must stay obviously synthetic (names/sources); no real customer PII.
- Rate limits / signup abuse controls remain on auth surfaces (existing auth threat model).

## Tests

- Non-admin → seed/clear rejected.
- Seed is idempotent when already active; clear then reseed works.
- Seeded objects are not visible from another tenant (RLS).
- Public `/demo` does not expose API tokens or tenant IDs.

## Related

- Runtime: `backend/app/services/onboarding_demo_seed.py`, `backend/app/api/v1/onboarding.py`
- UI: `SuccessPathReadinessPanel` load/clear demo CTAs; `hostflow-frontend/src/pages/public/DemoPage.tsx`
