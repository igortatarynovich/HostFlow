# Entity Field Composition CL1 — Candidate Inventory

**Status:** **PASS** — CL1 Gate closed by [#299](https://github.com/igortatarynovich/HostFlow/pull/299) / `b33ac205`; successor LI-1 ✅ [#300](https://github.com/igortatarynovich/HostFlow/pull/300)  
**Phase class:** platform  
**Branch:** `feat/entity-field-composition-cl1-inventory`  
**Parents:** [CL0 contract seal](entity-field-composition-cl0-contract-seal.md) · [Sequential queue](sales-to-comms-sequential-queue.md)

> CL1 observes live Candidate composition sources. It does not canonize country or document-type identity (Reference R3/R4). It does not ship membership/layout runtime (CL2+).

---

## Original Goal → Completion Proof

**Problem:** Candidate meaning still spreads across `CandidateProfile.config`, Entity Profile manifests, Field Registry, requirement packs, and frontend hardcodes. CL2 cannot start without a named inventory.

**Completion proof:** committed inventory artifact + regenerating scanner with `--check` gate. Rows name `code`, `source`, `tenant/module`, `enabled`, `required-as-found`, `consumers`, and `legacy usage` for the driver_ce path.

**False close:** runtime membership; alias/canonical tables; document-type normalization; tenant DB sweep in v1.

---

## Scope (v1)

| In scope | Out of scope |
|----------|--------------|
| `driver_ce_default` seed `field_configs` / `document_configs` | Per-tenant DB JSONB sweep |
| `recruitment.candidate.driver_ce` Entity Profile levels | CL2 membership runtime |
| Field Registry recruitment candidate fields | E8-bind / E8-eval |
| `recruitment.driver_ce_documents` pack slots/docs (observed codes) | Warehouse / office role variants |
| Frontend `profileUtils` / intake hardcodes (labeled) | Canonizing invalid codes |

---

## Artifacts

| Artifact | Path |
|----------|------|
| Inventory TSV | [entity-field-composition-cl1-inventory.tsv](entity-field-composition-cl1-inventory.tsv) |
| Scanner | `scripts/entity_field_composition/cl1_candidate_inventory.py` |
| Gate test | `backend/tests/entity_field_composition/test_cl1_inventory_gate.py` |

Regenerate: `python3 scripts/entity_field_composition/cl1_candidate_inventory.py --write`

---

## CL1 Gate (named)

PASS when:

1. Inventory artifact committed and scanner `--check` green.  
2. Rows cover field_configs, document_configs, entity profile levels, pack slots, and labeled screening-as-required observations.  
3. No canonical / alias / migration-required columns in artifact.

Unlocks: **LI-1** (not DR1 directly).

---

## History

- 2026-08-23: CL1 inventory slice opened — observe-only driver_ce path; throughput mode (prep before formal CL0 gate merge dependency).
