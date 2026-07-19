# Forms Product Layer P2.5 — Minimal Builder UI

**Status:** **COMPLETE**  
**Epic / P2:** [`forms-product-p2-builder.md`](forms-product-p2-builder.md)  
**Prerequisite:** P2.1–P2.4 **COMPLETE** · UI gate **OPEN** (`7164a66d` / #60)  
**Result:** Builder MVP complete (Catalog → Builder → Draft; Publish remains separate / P3)  

---

## Goal

First user-facing Builder UI as a **thin client** of frozen Catalog + composition commands + draft persistence.

---

## Delivered (minimal scope)

| Surface | Role |
|---------|------|
| Palette | Catalog Read Model |
| Search | Read Model query |
| Canvas | Ordered instances |
| Add / reorder / remove | Client composition edits |
| Properties panel | Builder Descriptor `config_fields` |
| Save / load draft | `forms.builder.draft_persistence.v1` |
| Dirty + revision conflict | CAS `expected_revision` → 409 UX |

**HTTP:** `/api/v1/platform/forms/builder/*`  
**UI:** `/app/settings/lead-forms/:formId/builder`  
**Entry:** Intake form detail → Open Builder  

---

## Explicitly out

Themes · public preview · publish wizard · analytics · conditional logic · layout/grid designer · CSS · responsive editor · multi-section DnD that changes composition model.

---

## After P2.5

Builder MVP closed. Full intended product loop:

```text
Field Catalog → Builder → Draft → Publish → Public Form → Submission
```

Publish UI remains **P3 LOCKED**. Next epic focus after Builder MVP: **Flights / Intake Routing** (Candidate Application vs Sales Inquiry separation).

---

## History

- 2026-07-19: UI gate opened after P2.4 (`7164a66d` / #60).  
- 2026-07-19: **COMPLETE** — minimal Builder UI + HTTP adapter.
