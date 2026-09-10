# Intake Readiness Gate

**Status:** **Accepted** (L2 contract — Intake Readiness freeze). Named gate **PASS** when machine tests hold.  
**Date:** 2026-09-10  
**Trusted base:** `feat/eso4-formalize` @ `18a2ee42`  
**Related:** [Recruitment Spine Orchestrator v1](../tasks/recruitment-spine-orchestrator-v1.md) · [HostFlow v1 Release Goal](hostflow-v1-release-goal.md)

**L0 checklist:** No new P-rule; no Passport/Manifest **shape** change; no Architecture RFC. Applies **P-02** / Strategy Lock (internal pipeline / campaign entities are not operator STOP conditions when system state already has vacancy + person). Does not open ESO-6. Does not amend [#359](https://github.com/igortatarynovich/HostFlow/pull/359). Does not merge into `integration`.

> SoT for **intake → actionable Recruitment Application**.  
> Machine: `intake_readiness.v1` in `backend/app/reference/intake_readiness.py`.  
> Gate tests: `backend/tests/platform/test_intake_readiness_gate.py`.  
> CI: `intake-readiness-gate`.

---

## Operator question (one)

Can a controlled Meta-like payload enter through `POST /api/v1/leads/meta` and become a normal Recruitment Application whose next action is **Fits**, without anyone writing canonical facts into the database by hand?

No second question is this gate. Transfer, Formalize, Started, and operator witness belong to Full Spine.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
SMTP transport, campaign-flight attribution, unmapped form answers, and a 500 on mapping configuration can stop a person **before** Recruitment. Those were being treated as “environment prerequisites”. They are product friction until proven necessary.

**Completion proof (named consumer):**  
One Meta-shaped webhook body, real vacancy/client configuration, handoff already enabled, no `INSERT`/`UPDATE` of canonical facts after ingest:

`POST /leads/meta` → processed Application → `next_action = fits`.

**False close (reject):** patching `citizenship` after intake; enabling handoff by rewriting a shared funnel; claiming Full Spine PASS; treating SMTP `delivery_failed` as missing consent when notice/consent is already in the payload.

---

## Hard locks

1. **Consent/RODO validity is not SMTP delivery.** `delivery_failed` is an operational record. If the payload already carries notice/consent at source, intake stays actionable.  
2. **Known ad_id / form_id / page_id / vacancy mapping must route Recruitment without a campaign-flight STOP.** Flight remains acquisition attribution, not a domain requirement to exist as a person in Recruitment.  
3. **Form answers that recruitment/employment need (citizenship, experience, categories) become canonical facts through mapping/normalizer.** They must not remain only in `field_answers`.  
4. **Staff mapping configuration must not 500** on `require_elevated_reason_or_raise`.  
5. **When recruitment facts are sufficient, Application `next_action` is `fits`.** Not Create candidate, not an empty next action, not `needs_routing` for campaign-flight.

---

## Out of scope

- ESO Accept / Employability / Formalize / Employee / Started  
- #359 one-card UI  
- Meta Graph retrieval (Meta Source Gate)  
- Changing POLTRAKT / Rock Cargo funnels to obtain a synthetic PASS
