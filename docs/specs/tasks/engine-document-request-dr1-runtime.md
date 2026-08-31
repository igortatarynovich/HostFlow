# Engine → Document Request DR1-runtime

**Status:** **PASS** [#313](https://github.com/igortatarynovich/HostFlow/pull/313)  
**Phase class:** platform  
**Branch (docs):** `docs/queue-post-overlay-amendment`  
**Branch (code):** `feat/engine-document-request-dr1-runtime`  
**Parents:** [DR1-contract](engine-document-request-dr1-contract.md) · [CL7 Engine evaluation](entity-field-composition-cl7-engine-eval.md) · [Vacancy Overlay Contract](entity-profile-vacancy-overlay-contract.md) · [Documents Platform E7](documents-platform-e7-document-requests.md) · [Platform Reference Identity SoT](platform-reference-identity-sot.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [trusted-base reproduction 2026-08-31](../gates/dr1-runtime-trusted-base-repro.md)

> DR1-runtime is the **write** half of Engine → Hub outstanding ask. DR1-contract already projects CL7 evaluation to `engine_to_hub_outstanding_ask.v1` rows. This slice **persists** those rows onto Hub (`documents.hub_adapter_v1`) so evaluation consumers may run. **Not** CL8. **Not** Engine v2. **Not** E8-bind / E8-eval. **Not** a Hub request table. **Not** Catalog `document.requested`. **Not** mass generation. **Not** Overlay SoT. Overlay is an input to evaluate; this producer writes asks.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
CL7 + Overlay can answer “ready or not, and why”, and DR1-contract can project document blockers to Hub ask **shape**, but nothing named **creates** Hub outstanding asks. Without DR1-runtime the next slice will treat projection as persistence, mint a Hub request table, emit Catalog `document.requested`, start E8-eval (required/optional / packages), invent CL8, or mass-generate asks across entities.

**Completion proof (named consumer):**  
`engine_to_hub_outstanding_ask.v1` **write** for `recruitment.candidate.driver_ce` — CL7 `evaluate` (with Overlay merge as defined input) → DR1-contract projection → Hub outstanding-ask persistence on `documents.hub_adapter_v1` with canonical `document_type_code` only. D4 **places** the Documents surface that already **reads** E7 outstanding asks. D4 **places**; Hub owns persistence. Persist is keyed by Document Link identity (required type + entity) on the existing adapter — **not** a new Hub request table.

**False close:** numbering this as CL8; Engine v2; E8-bind identity migration; E8-eval required/optional / packages / OCR matching; Hub request / reminder table; Catalog `document.requested`; mass generation; treating Overlay as this producer; screening as `required=true` on a field; writing asks onto Profile membership.

---

## Scope

| In scope | Out of scope |
|----------|--------------|
| Engine may **create** Hub outstanding asks | Overlay SoT / CL7 evaluate rewrite |
| Persistence of `engine_to_hub_outstanding_ask.v1` onto Hub | Mass generation across entities / tenants |
| Evaluation consumers may run (read Hub asks) | Hub request table; Catalog `document.requested` |
| Canonical `document_type_code` only (R3/R4) | E8-bind / E8-eval; remaining-consumer identity bind |
| Named leftover of Engine→Request after CL | CL8; Engine v2; Forms P3; Billing; AI |

---

## Contract shape

```text
CL7 evaluate(entity, profile, overlay, process_point)
  → DR1-contract project_engine_evaluation_to_outstanding_asks(...)
  → persist Hub outstanding asks on documents.hub_adapter_v1
     [{doc_type: <canonical>, state: missing|requested|problem}]
```

Reject: CL8; boolean Engine; Hub request table; Catalog event; mass generate; E8-eval; Overlay implementation on Profile; writing asks from a second producer.

This slice **does not** mint Requirement Engine v2, **does not** bind remaining Documents consumers (E8-bind), and **does not** evaluate required/optional applicability (E8-eval). Overlay remains [Vacancy Overlay Contract](entity-profile-vacancy-overlay-contract.md). Projection remains [DR1-contract](engine-document-request-dr1-contract.md).

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file |
| Runtime write | `backend/app/requirement_rules/engine_outstanding_ask_runtime.py` |
| Hub persist | `persist_outstanding_asks_via_contract` on `documents.hub_adapter_v1` |
| D4 bind | Documents surface reads Hub asks (E7); Engine writes them |
| Boundary guard | `scripts/architecture/check_engine_outstanding_ask_writer_boundary.py` |
| Named CI | **DR1 Runtime Gate** |

---

## DR1 Runtime Gate (named)

PASS when:

1. Brief + runtime writer committed.  
2. Engine may create Hub outstanding asks from CL7 evaluation (Overlay as defined input).  
3. Rows use canonical `document_type_code` only; states ∈ {missing, requested, problem}.  
4. No Hub request table; no Catalog `document.requested`; no mass generation.  
5. Not E8-bind; not E8-eval; not CL8; not Engine v2.  
6. D4 still places Documents / Engine-eval zones; Information / Q&A / Flight-map unchanged.  
7. Boundary guard reports exactly one Hub outstanding-ask **writer** for this contract.  
8. Named CI job exists for the DR1 Runtime Gate.

Unlocks: later Product via **queue amendment** — named **E8-bind** after this Gate (**PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f`). E8-bind unlocks **E8-eval** ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`. Does **not** auto-start OCR. Do **not** invent CL8.

---

## Queue position

**Depends on:** DR1-contract Gate ✅ (#302) · Reference R5 Gate ✅ (#297) · Vacancy Overlay Gate ✅ (#311 / `7649544d`) · Reference Program Exit Gate ✅ (#298 / `ff0b914c`)  
**Unlocks:** [E8-bind](documents-platform-e8-bind.md) ✅ [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` → [E8-eval](documents-platform-e8-eval.md) ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324)  
**Does not:** invent CL8; start OCR; mint a Hub request table; mass-generate asks; rewrite Overlay / CL7 evaluate

---

## History

- 2026-08-31: Trusted-base CI job is red; GitHub logs for run #326 are gone. Local reproduction of the same pytest target fails 1/10 — see [dr1-runtime-trusted-base-repro.md](../gates/dr1-runtime-trusted-base-repro.md). Not a reopen of this slice. Not Launch-ops.
- 2026-08-25: E8 Required-Doc Evaluation Gate PASS [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`. Product = **none this amendment**. Not OCR auto-start. Not CL8.
- 2026-08-25: Queue amendment after E8-bind Gate PASS names **E8-eval** as Active Product (brief; feat locked). Not OCR auto-start. Not CL8.
- 2026-08-25: Queue amendment after E8 Canonical Type Bind Gate PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f`. No named Product successor. E8-eval unlocked (not scheduled).
- 2026-08-25: Queue amendment after DR1 Runtime Gate PASS names **E8-bind** as Active Product (brief; feat locked). Not E8-eval auto-start. Not CL8.
- 2026-08-25: DR1-runtime feat **PASS** [#313](https://github.com/igortatarynovich/HostFlow/pull/313) — Engine may create Hub outstanding asks on `documents.hub_adapter_v1`. Not CL8. Not E8. Not mass generation.
- 2026-08-25: DR1-runtime feat opened — Engine may create Hub outstanding asks on `documents.hub_adapter_v1`. Not CL8. Not E8. Not mass generation.
- 2026-08-25: DR1-runtime opened (feat locked) after Vacancy Overlay Gate PASS [#311](https://github.com/igortatarynovich/HostFlow/pull/311) / `7649544d` and Reference Program Exit PASS [#298](https://github.com/igortatarynovich/HostFlow/pull/298) / `ff0b914c`. Engine may create Hub outstanding asks. Not CL8. Not E8. Not mass generation.
