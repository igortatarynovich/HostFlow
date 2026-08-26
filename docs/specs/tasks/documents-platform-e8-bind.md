# Documents Platform E8-bind — Canonical Type Bind

**Status:** **PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` (brief COMPLETE; feat `b0129565`)  
**Phase class:** platform  
**Branch (docs):** `docs/queue-post-dr1-runtime-amendment` ✅ [#319](https://github.com/igortatarynovich/HostFlow/pull/319) · `docs/queue-post-e8-bind-amendment` (this PR)  
**Branch (code):** `feat/documents-platform-e8-bind` ✅ [#321](https://github.com/igortatarynovich/HostFlow/pull/321)  
**Parents:** [Documents Platform E7](documents-platform-e7-document-requests.md) · [DR1-runtime](engine-document-request-dr1-runtime.md) · [Platform Reference Identity SoT](platform-reference-identity-sot.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase E](../architecture/platform-completion-roadmap.md) · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [Documents Public Contract](../architecture/documents-public-contract.md) · [`document-type-registry-v1.json`](../platform/document-type-registry-v1.json) · [`document-type-legacy-aliases-v1.json`](../platform/document-type-legacy-aliases-v1.json)

> E8-bind is the **identity** half of remaining Documents consumers. Reference R3 is existence SoT; R4 is the alias registry; DR1-runtime already **writes** Hub outstanding asks with canonical `document_type_code`. This slice makes remaining **display / select / stored identity** bind to canonical registry codes. **Not** E8-eval. **Not** CL8. **Not** mass D3–D9 `documents` bind. **Not** a Hub request table. **Not** Catalog `document.requested`. **Not** required/optional, applicability, packages, or OCR matching.

---

## Original Goal → Completion Proof

**Problem this phase must permanently remove:**  
After R3/R4, type existence and aliases are SoT, and DR1-runtime persists canonical ask codes, but remaining type consumers may still **display, select, or persist** alias / legacy / ORM-default codes as if they were identity. Without E8-bind the next slice will treat alias display as canonical bind, mass-bind D3–D9, start E8-eval (required/optional / packages / OCR), invent CL8, or mint a second type catalog.

**Completion proof (named consumer):**  
**Candidate Entity Workspace — D4 Documents surface** (`CandidateEntityWorkspacePanel` / `/app/candidates/:id` documents zone). Display, select, and stored Hub `document_type_code` (including Engine-written outstanding asks already on the adapter) use **canonical registry codes** only. Aliases resolve through R4 `document-type-legacy-aliases-v1.json` — they are not stored identity. D4 **places**; Document Hub owns type identity.

**False close:** numbering this as CL8; collapsing into one E8 with E8-eval; mass D3–D9 D2 `documents` bind; E8-eval required/optional / packages / OCR matching / e-sign; Hub request / reminder table; Catalog `document.requested`; treating R4 alias use as the bind; treating `DocumentTypeDefinition.canonical_ref_code` default `"other"` as existence SoT; Foundation ✅.

---

## Scope

| In scope | Out of scope |
|----------|--------------|
| Remaining consumers bind to **canonical** document types | E8-eval (required/optional, applicability, packages, OCR matching) |
| Display / select canonical types | Mass D3–D9 D2 `documents` bind |
| Identity migration (stored codes → registry canonical) | Hub request table; Catalog `document.requested` |
| R4 aliases as **resolve-only**, not stored identity | CL8; Engine v2; Overlay rewrite; R5 `merge(pack, tenant_delta)` |
| Named leftover of Documents after DR1-runtime | Forms P3; Billing; AI; Foundation ✅ |

---

## Contract shape

```text
document-type-registry-v1.json     = existence / canonical_ref_code
document-type-legacy-aliases-v1.json = resolve-only (R4)
  → D4 Documents surface display / select / persist canonical codes
  → D8 HR bind unchanged (same canonical identity; not a second proof)
  → D3 / D5–D7 / D9 still omit documents
```

Reject: E8-eval; CL8; mass D-slot bind; Hub request table; Catalog event; second type dictionary; ORM `"other"` default as SoT.

This slice **does not** evaluate required/optional applicability (E8-eval), **does not** bind remaining Entity Workspace `documents` slots, and **does not** rewrite DR1-runtime / Overlay / CL7.

---

## Artifacts

| Artifact | Path |
|----------|------|
| Brief | this file |
| Identity bind | `persist_canonical_type_identity_via_contract` on `documents.hub_adapter_v1` |
| D4 bind | existing Documents surface; this slice binds **type identity**, not a new slot |
| Named CI | **Documents Platform E8 Canonical Type Bind Gate** (`tests/platform/test_documents_e8_canonical_type_bind_gate.py`) |

---

## Documents Platform E8 Canonical Type Bind Gate (named)

**Outcome:** **PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` (feat `b0129565`). CI job Documents Platform E1–E8 green.

PASS when:

1. Brief + identity bind committed.  
2. D4 Documents surface displays and selects canonical registry types only.  
3. Stored Hub `document_type_code` for the proof consumer is canonical; aliases resolve via R4 only.  
4. No Hub request table; no Catalog `document.requested`; no mass D3–D9 bind.  
5. Not E8-eval; not CL8; not Engine v2; not Foundation ✅.  
6. D4 still places Documents; D8 bind unchanged; D3 / D5–D7 / D9 still omit `documents`.  
7. Named CI job exists for the E8 Canonical Type Bind Gate.

Evidence: D4 Documents (`/app/candidates/:id`) display / select / persist canonical registry codes. R4 aliases (`code95`, `tacho_card`, …) are resolve-only, not stored identity. Adapter `documents.hub_adapter_v1`: `persist_canonical_type_identity_via_contract`, `list_canonical_types_for_select_via_contract`; empty input does not become `"other"`. Public resolve: additive `canonical_types`, no contract id bump. D4 UI: native `<select className="input">`; `data-e8-bind="true"` `data-e8-eval="false"`.

Unlocks: **E8-eval** ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6` ([brief](documents-platform-e8-eval.md)). Later Product via **queue amendment**. No named successor this amendment. Do **not** auto-start OCR. Do **not** invent CL8.

---

## Queue position

**Depends on:** Reference R3 Gate ✅ (#295) · Reference R4 Gate ✅ (#296) · DR1 Runtime Gate ✅ (#313 / `e6978fe2`)  
**Unlocks:** [E8-eval](documents-platform-e8-eval.md) ✅ [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`  
**Does not:** invent CL8; start OCR; mass-bind D3–D9; mint a Hub request table; rewrite Overlay / CL7 / DR1-runtime

---

## History

- 2026-08-25: E8 Required-Doc Evaluation Gate **PASS** [#324](https://github.com/igortatarynovich/HostFlow/pull/324) / `19c95ef6`. Product Track → **none this amendment**. Not OCR auto-start. Not CL8.
- 2026-08-25: Queue amendment after E8-bind Gate PASS names **E8-eval** Active Product (brief; feat locked). Not OCR auto-start. Not CL8.
- 2026-08-25: Documents Platform E8 Canonical Type Bind Gate **PASS** [#321](https://github.com/igortatarynovich/HostFlow/pull/321) / `8246421f` (feat `b0129565`). Brief COMPLETE. No named Product successor this amendment. E8-eval unlocked (not scheduled; brief not opened). Not CL8. Not mass D3–D9 bind. Foundation stays 🔄.
- 2026-08-25: E8-bind feat opened — D4 Documents display / select / persist canonical registry codes; R4 aliases resolve-only. Named Documents Platform E8 Canonical Type Bind Gate. Not E8-eval. Not CL8. Not mass D3–D9 bind.
- 2026-08-25: E8-bind opened (feat locked) after DR1 Runtime Gate PASS [#313](https://github.com/igortatarynovich/HostFlow/pull/313) / `e6978fe2`. Remaining consumers bind to canonical document types. Not E8-eval. Not CL8. Not mass D3–D9 bind.
