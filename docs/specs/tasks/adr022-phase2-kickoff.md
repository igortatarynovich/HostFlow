# ADR-022 Phase 2 — kickoff (Product B on current architecture)

**Status:** **CLOSED / historical** — delivery slices 1–7 DONE through [#99](https://github.com/igortatarynovich/HostFlow/pull/99) (2026-07-20), including Capability UI `a2a413e9` / [#96](https://github.com/igortatarynovich/HostFlow/pull/96), manual ClientAccount creation `6cbb1161` / [#97](https://github.com/igortatarynovich/HostFlow/pull/97) and Pipeline v1 wiring [#98](https://github.com/igortatarynovich/HostFlow/pull/98)/[#99](https://github.com/igortatarynovich/HostFlow/pull/99). This file names no successor: sequencing lives in the [sequential queue](sales-to-comms-sequential-queue.md) (Product Track = RPM-1)  
**Date:** 2026-07-20  
**Trusted base:** `integration/release-product-a-b` @ `e276e81f`+ (fast-forward only)  
**Supersedes naming:** not “ADR022 audit” — audit is **done** ([`adr022-product-b-local-commits-audit.md`](adr022-product-b-local-commits-audit.md))  
**Normative parents:** ADR-022 · ADR-021 · Flights R3.5 · INV-16 · INV-17 · [`repository-operational-canon.md`](../../governance/repository-operational-canon.md)

**Canonical Flow Spec (slice 1):** [`../workflows/adr022-phase2-sales-only-capability-flow.md`](../workflows/adr022-phase2-sales-only-capability-flow.md)  
**Convert mapping (slice 2):** [`sales-questionnaire-convert-mapping.md`](sales-questionnaire-convert-mapping.md)  
**Ambiguous match review (slice 3):** [`sales-ambiguous-match-review.md`](sales-ambiguous-match-review.md)  
**Traceability (slice 4):** [`sales-inquiry-traceability.md`](sales-inquiry-traceability.md)  
**Pipeline v1 seal:** [`../architecture/sales-domain-pipeline-v1.md`](../architecture/sales-domain-pipeline-v1.md)  
**Creation Origins:** [`../architecture/client-account-creation-origins-v1.md`](../architecture/client-account-creation-origins-v1.md)  
**Sequential product queue (locked):** [`sales-to-comms-sequential-queue.md`](sales-to-comms-sequential-queue.md)

---

## Spine (build around this — nothing else)

```text
SalesInquiry
  → Flights destination
  → Capability (Sales-owned)
  → Review (ambiguous match / manager signal)
  → Convert (ClientAccount mapping)
  → Traceability (inquiry ↔ questionnaire ↔ client)
```

**No references to the old Capability Wizard implementation** as a port target.  
Historical commits on `feat/adr022-intake-policy-phase1-backend` are a **requirements scrapbook only**.

---

## Non-goals (explicit)

| Forbidden | Why |
|-----------|-----|
| Cherry-pick / rebase of `7dac9ada` wizard | Sales + Recruitment in one catalog — L0 / INV-16 fail |
| Lead as long-term Sales SoT | SalesInquiry owns the commercial result |
| Sales ↔ Recruitment create/send shortcuts | Module independence |
| Wholesale merge of recovery / old feature branch | Archive ≠ product |
| Mixed integrity + product PR | Repository Operational Canon |

---

## Delivery slices (thin PRs from integration)

| Order | Branch hint | Outcome | Status |
|-------|-------------|---------|--------|
| 1 | `docs/f3-b-10-sales-capability-flow` | Flow Spec | **Done** |
| 2 | `feat/sales-questionnaire-convert-mapping` | Convert mapping | **Done** |
| 3 | `feat/sales-ambiguous-match-review` | SalesInquiry-owned review | **Done** |
| 4 | `feat/sales-inquiry-traceability` | Immutable lineage (**no UI**) | **Done** |
| 4b | `docs/sales-domain-pipeline-v1-seal` | Architectural revision + seal | **Done** |
| 4c | `docs/client-account-creation-origins-v1` | ClientAccount origins (conversion + manual) | **Done** |
| Q | `docs/sales-comms-sequential-queue` | Lock Sales→Comms product sequence | **CURRENT** |
| 5 | `feat/sales-capability-ui` | Display-only Capability / Review / Convert / Traceability | **NEXT** after Q |
| 6 | `feat/manual-client-account-creation` | `create_client_account_manually` | queued |
| 7 | `fix/sales-pipeline-v1-product-wiring` | Close Pipeline v1 §3 product GAPs | queued |
| 8+ | Communication Stages 4–7 | See sequential queue | **after Sales 5–7** |

Stop after each PR for ownership / INV-16 review.

**Linear order (locked):** … → Pipeline seal → Origins → **Capability UI → Manual create → Pipeline wiring → Communication (outbound binding → signatures → composer → integrity)**.

Domain contracts are sealed; **product wiring gaps remain** (Pipeline v1 §3). One product slice at a time — see [`sales-to-comms-sequential-queue.md`](sales-to-comms-sequential-queue.md).

---

## Requirements extracted from history (ideas only)

Use audit classifications; do **not** open old tree as implementation base:

- Capability-first create (manager picks direction, not Entity Profile knobs)  
- Post-save card ends in a working tool (send / copy / preview)  
- Usage modes: personal invite from inquiry vs public link  
- Ambiguous public match → manager review  
- Convert maps industry / budget / notes from questionnaire  
- Traceability across inquiry, questionnaire form, client  

Recruitment Capability belongs to a **Recruitment-owned** surface later — out of Phase 2 Sales spine.

---

## Start gate

```bash
make repo-health
# must PASS on integration tip
```
