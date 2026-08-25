# Documents Platform E8-eval — Required-Doc Evaluation

**Status:** **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6` (brief COMPLETE; feat `821adf33`)  
**Phase class:** platform  
**Branch (docs):** `docs/queue-schedule-e8-eval` ✅ [#323](https://github.com/igortatarynovich/HostFlow/pull/323) · `docs/queue-post-e8-eval-amendment` (this PR)  
**Branch (code):** `feat/documents-platform-e8-eval` ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324)  
**Parents:** [Documents Platform E8-bind](documents-platform-e8-bind.md) · [Documents Platform E7](documents-platform-e7-document-requests.md) · [DR1-runtime](engine-document-request-dr1-runtime.md) · [CL7 Engine evaluation](entity-field-composition-cl7-engine-eval.md) · [Vacancy Overlay Contract](entity-profile-vacancy-overlay-contract.md) · [Platform Reference Identity SoT](platform-reference-identity-sot.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase E](../architecture/platform-completion-roadmap.md) · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md) · [Documents Public Contract](../architecture/documents-public-contract.md)

> E8-eval is the **evaluation** half of remaining Documents consumers. E8-bind already binds display / select / stored identity to canonical registry codes. Reference R5 already defines `merge(pack, tenant_delta)`. CL7 already returns structured `ready`/`not_ready` + blockers. This slice makes remaining **required / optional / applicability** evaluation bind to that merged policy with canonical type codes. **Not** OCR product. **Not** a packages Hub table. **Not** CL8. **Not** mass D3–D9 `documents` bind. **Not** a Hub request table. **Not** Catalog `document.requested`. **Not** Engine v2. **Not** rewriting CL7 / Overlay / DR1-runtime / E8-bind.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After E8-bind, type identity is canonical, and after R5 the pack/tenant merge exists, but remaining Documents consumers may still treat identity bind, screening `required=true` on a field, or Hub outstanding asks as **required/optional applicability**. Without E8-eval the next slice will treat canonical display as evaluation, mint OCR matching, invent a packages product, invent CL8, mass-bind D3–D9, or mark Foundation ✅.

**Completion proof (named consumer):**  
**Candidate Entity Workspace — D4 Documents surface** (`CandidateEntityWorkspacePanel` / `/app/candidates/:id` documents zone). Required / optional / blocked document types for the proof profile come from R5 `merge(pack, tenant_delta)` (Overlay as already-defined CL7 input) using **canonical registry codes** only. D4 **places**; Document Hub + Reference own evaluation.

**False close:** numbering this as CL8; collapsing into one E8 with E8-bind; treating E8-bind identity as evaluation; OCR product / OCR↔requirement matching; minting a Hub packages / request / reminder table; Catalog `document.requested`; mass D3–D9 D2 `documents` bind; rewriting CL7 evaluate / Overlay / DR1-runtime; screening as `required=true` on a field as Documents SoT; Foundation ✅.

---

## Scope

| In scope | Out of scope |
|----------|--------------|
| Required / optional / blocked **applicability** of canonical document types | OCR product; OCR↔requirement matching; e-sign |
| Candidate requirement evaluation from R5 `merge(pack, tenant_delta)` | Minting a Hub packages table / packages product |
| Consume existing R5 packs as policy input | Mass D3–D9 D2 `documents` bind |
| Named leftover of Documents after E8-bind | Hub request table; Catalog `document.requested` |
| Overlay as already-defined CL7 input (`document_types`) | CL8; Engine v2; Overlay rewrite; E8-bind rewrite; Forms P3; Billing; AI; Foundation ✅ |

---

## Contract shape

```text
R5 merge(pack, tenant_delta) + Overlay (defined CL7 input)
  → required | optional | blocked  (canonical document_type_code only)
  → D4 Documents surface shows applicability vs Hub links / outstanding asks
  → D8 HR bind unchanged (same evaluation contract; not a second proof)
  → D3 / D5–D7 / D9 still omit documents
```

Reject: OCR product; packages Hub table; CL8; mass D-slot bind; Hub request table; Catalog event; treating identity bind as evaluation; screening `required=true` as Documents SoT.

This slice **does not** rewrite CL7 `evaluate`, **does not** rewrite Overlay / DR1-runtime / E8-bind identity, **does not** bind remaining Entity Workspace `documents` slots, and **does not** ship OCR.

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file |
| Evaluation bind | `evaluate_required_doc_applicability_via_contract` on `documents.hub_adapter_v1` |
| D4 bind | existing Documents surface; this slice binds **applicability**, not a new slot |
| Named CI | **Documents Platform E8 Required-Doc Evaluation Gate** (`tests/platform/test_documents_e8_required_doc_eval_gate.py`) |

---

## Documents Platform E8 Required-Doc Evaluation Gate (named)

**Outcome:** **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6` (feat `821adf33`). CI job Documents Platform E1–E8 green.

PASS when:

1. Brief + evaluation bind committed.  
2. D4 Documents surface evaluates required / optional / blocked from R5 merge using canonical registry types only.  
3. Existing R5 packs are policy input; no Hub packages table.  
4. No OCR product; no Hub request table; no Catalog `document.requested`; no mass D3–D9 bind.  
5. Not CL8; not Engine v2; not Foundation ✅; not rewriting CL7 / Overlay / DR1-runtime / E8-bind.  
6. D4 still places Documents; D8 bind unchanged; D3 / D5–D7 / D9 still omit `documents`.  
7. Named CI job exists for the E8 Required-Doc Evaluation Gate.

Evidence: D4 Documents (`/app/candidates/:id`) required / optional / blocked from R5 `merge(pack, tenant_delta)`; Overlay = typed CL7 input `document_types`; canonical registry codes only. Adapter `documents.hub_adapter_v1`: `evaluate_required_doc_applicability_via_contract` / `project_required_doc_applicability_via_contract`; additive `applicability`; no contract id bump. D4 UI: `data-e8-eval="true"` `data-applicability`. D4 + D8 stay bound. D3 / D5–D7 / D9 stay unbound. Screening `required=true` is not Documents SoT.

Unlocks: later Product via **queue amendment**. No named successor this amendment. Do **not** auto-start OCR / packages product / CL8. Do **not** mark Foundation ✅.

---

## Queue position

**Depends on:** Reference R5 Gate ✅ (#297) · E8 Canonical Type Bind Gate ✅ (#321 / `8246421f`) · Reference Program Exit Gate ✅ (#298 / `ff0b914c`)  
**Unlocks:** later Product via queue amendment  
**Does not:** invent CL8; start OCR; mint a packages / request table; mass-bind D3–D9; rewrite Overlay / CL7 / DR1-runtime / E8-bind

---

## History

- 2026-08-25: Documents Platform E8 Required-Doc Evaluation Gate **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6` (feat `821adf33`). Brief COMPLETE. No named Product successor this amendment. Not OCR auto-start. Not CL8. Not mass D3–D9 bind. Foundation stays 🔄.
- 2026-08-25: E8-eval feat opened — D4 required / optional / blocked from R5 merge; Overlay as CL7 input; named Documents Platform E8 Required-Doc Evaluation Gate. Product Track stays [E8-eval](documents-platform-e8-eval.md). Engineering stays DONE. Not OCR. Not CL8. Not mass D3–D9 bind.
- 2026-08-25: E8-eval opened (feat locked) after E8 Canonical Type Bind Gate PASS [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` and queue amendment [#322](https://github.com/igortatarynovich/HostFlow/pull/322) / `196aff39`. Required / optional / applicability from R5 merge. Not OCR. Not CL8. Not mass D3–D9 bind.
