# Intake Routes — Meta Form → OwnCompany (Phase 0 Bridge)

**Status:** DEPRECATED → superseded by [`intake-routing-foundation.md`](intake-routing-foundation.md)  
**Shipped:** 2026-06-05 (tactical unblock for Meta B2B ads)

## Purpose

Temporary runtime bridge before **Intake Routing Foundation**. Resolves Meta `form_id` → OwnCompany + `lead_target_type` without a canonical source registry.

**Do not extend** this model for TikTok, WhatsApp, website, or API channels. New work goes to Intake Source Profiles + Bindings.

## What exists in code (Phase 0)

- Table `meta_form_routes`
- Column `leads.lead_target_type`
- `backend/app/modules/leads/intake_route.py`
- API `GET/PUT /api/v1/settings/leads/meta/forms/{form_id}/route`
- Meta LeadHub UI — «Intake route» block

## Migration target

| Phase 0 | Foundation |
|---------|------------|
| `meta_form_routes` | `intake_source_bindings` (`provider=meta`, `external_key=form_id:…`) |
| `lead_target_type` | `route_intent` on profile + denormalized on Lead |
| `intake_route.py` | `IntakeRouter.resolve()` |

See [`intake-routing-foundation.md` §8](intake-routing-foundation.md#8-migration-from-phase-0-meta_form_routes).

## Operational use (WHI)

Until PR-4 lands, configure Meta LeadHub → Intake route for B2B form:

- OwnCompany: **Work Host Services**
- Lead target: **Client lead** (maps to `sales_inquiry`)

This stops auto-creation of Candidates from carrier ads.
