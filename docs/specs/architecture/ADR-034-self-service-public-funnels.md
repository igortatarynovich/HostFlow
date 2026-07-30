# ADR-034: Canonical self-service public funnels (Growth / Auth / Candidate)

## Status

Accepted (architecture). Runtime delivery is phased — see [`self-service-success-path.md`](../journeys/self-service-success-path.md).

## Context

HostFlow’s growth bottleneck is not missing CRM features. It is the gap between a first-time visitor and first value: unclear positioning, fragmented public entry surfaces, and incomplete guided setup.

Today the SPA already exposes:

- one Growth marketing shell (`/` → `CrmLandingPage`, SEO pages, `/signup`);
- Auth (`/login`, password reset, invite);
- Candidate / client public intake (`/public/*`, `/forms/*`, `/client-portal`).

Additionally, orphan and legacy surfaces (`PublicLanding.tsx` unwired, `/public/apply-old/:token`) create parallel “landing” UX and confuse product IA. Operator CRM `/app/marketing` is acquisition ops — not a public product homepage.

## Decision

1. **Exactly three canonical public funnels** on the shell SPA. No fourth independent product landing.

| Funnel | Canonical entry | Purpose | Conversion / next step |
|--------|-----------------|---------|------------------------|
| **Growth** | `/` (SEO pages deepen `/` → same CTA) | Sell outcome; explain how it works; pricing | `/signup?plan=` |
| **Auth** | `/login` | Returning operators | App shell / `?next=` module handoff |
| **Candidate** | `/public/intake` → `/public/apply/:token` | Candidate questionnaire / docs / status | Tokenized apply + status |

2. **SEO pages are Growth variants**, not separate landings: unique Title / H1 / body / FAQ, single primary CTA → `/signup` (or `/pricing` then signup).

3. **B2B tokenized forms** (`/forms/company-intake/:token`, `/forms/client-inquiry/:token`, `/client-portal`) stay under the Candidate/client public cluster as **contracted intake**, not Growth marketing.

4. **Forbidden:** new top-level marketing apps; unwired alternate product landings; parallel “homepage” UX for the same buyer journey.

5. **Legacy cleanup (normative):**
   - `/public/apply-old/:token` → redirect to `/public/apply/:token`;
   - remove or never remount orphan `PublicLanding`;
   - aspirational sitemap names in `docs/pipedesign.md` (`/product/*`, `/guides/*`) must not ship as a second IA — prefer shipped `/features|/use-cases|/comparison` until FAQ/docs routes exist under Growth.

6. **Post-signup Success Path** (Growth continuation) is product surface, not marketing chrome: short company identity form → **guided readiness UI** (checklist + next CTA + empty states) inside the normal shell → first vacancy/lead value. Spec: [`self-service-success-path.md`](../journeys/self-service-success-path.md). **Not** an 8-step Setup Wizard as the primary activation product.

7. **`/app/marketing`** remains operator Acquisition CRM only ([ADR-024](ADR-024-acquisition-campaigns-intake-routing.md)).

### Positioning rule (Growth)

Hero and primary copy answer four questions in the first viewport:

1. What is it?
2. Who is it for?
3. What do I get?
4. Why this (vs chaos / spreadsheets / generic CRM)?

Copy sells **result** (e.g. close vacancies faster via Meta / WhatsApp / forms → owned pipeline), not a feature list.

## Consequences

1. All Growth CTAs converge on `/signup` → platform setup → guided first value.
2. Candidate UX never competes with Growth homepage messaging.
3. FAQ hub, docs, academy, demo tenant, and SEO factory extend Growth under this ADR — they do not invent new funnels.
4. Activation expands existing platform setup + setup hub / launchpad as a **readiness interface**; it does not create a second public landing or a forced multi-step wizard for optional steps (Meta, invite, vacancy).

## Alternatives considered

- **Single merged public surface** (marketing + candidate intake): rejected — different trust, SEO (`noindex` on apply), and threat model ([`public-links.md`](../../security/threat-models/public-links.md)).
- **Separate marketing site / second SPA:** rejected — duplicates IA and drift vs `pipedesign` / UI platform ([ADR-011](ADR-011-hostflow-ui-platform-standard.md)).
- **Keep apply-old and orphan landings:** rejected — fragments conversion measurement and support.
- **8-step Setup Wizard as primary activation:** rejected in favor of guided readiness UI (checklist + next CTA + empty states); only company identity stays a short mandatory form.

## Cross-references

- Journey / phased delivery: [`self-service-success-path.md`](../journeys/self-service-success-path.md)
- Public intake: [ADR-013](ADR-013-public-intake-strategy.md)
- Plans SoT for pricing honesty: [`plans-matrix.md`](../plans-matrix.md)
- Visual / IA notes: [`pipedesign.md`](../../pipedesign.md)
- Page registry: [`REF-UI-000-PAGE_REGISTRY.prefill.md`](../frontend/REF-UI-000-PAGE_REGISTRY.prefill.md)
- Catalog linkage: [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)

## History

- 2026-07-30: Accepted — three public funnels; Growth Success Path as product layer; legacy entry cleanup normative.
- 2026-07-30: Clarified activation UX — **guided readiness UI**, not 8-step Setup Wizard ([`self-service-success-path.md`](../journeys/self-service-success-path.md)).
- 2026-07-30: Phase 4 Wave-2 SEO factory — catalog + `SeoCatalogPage` (8 industry/role/integration pages); Wave-1 hand pages remain.
