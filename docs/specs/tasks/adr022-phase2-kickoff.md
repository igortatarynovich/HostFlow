# ADR-022 Phase 2 — kickoff (Product B on current architecture)

**Status:** READY TO START  
**Date:** 2026-07-20  
**Trusted base:** current `integration/release-product-a-b` tip (fast-forward only)  
**Supersedes naming:** not “ADR022 audit” — audit is **done** ([`adr022-product-b-local-commits-audit.md`](adr022-product-b-local-commits-audit.md))  
**Normative parents:** ADR-022 · ADR-021 · Flights R3.5 · INV-16 · INV-17 · [`repository-operational-canon.md`](../../governance/repository-operational-canon.md)

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

| Order | Branch hint | Outcome |
|-------|-------------|---------|
| 1 | `docs/f3-b-10-sales-capability-flow` | Flow Spec: Sales-only Capability, ADR-022 axes, Flights + Pipeline citations |
| 2 | `feat/sales-questionnaire-convert-mapping` | Convert + invite enrichment from questionnaire fields |
| 3 | `feat/sales-ambiguous-match-review` | Review signal on **SalesInquiry** (not Lead.stage as SoT) |
| 4 | `feat/sales-capability-create-card` | Sales-only create + post-save card (new UI) |
| 5 | `feat/sales-inquiry-traceability-ui` | Traceability panel on SalesInquiry / client-acquisition paths |

Stop after each PR for ownership / INV-16 review.

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

Then open slice 1 as docs-only PR.
