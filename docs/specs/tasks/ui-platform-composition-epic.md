# UI Platform composition epic

**Status:** Active (runtime follow-on to ADR-043)  
**Canon:** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md) · L2 [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md)  
**Does not amend L0.** Visual tokens remain [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md).

This is an **implementation epic**, not a new design-spec program. Do not start with marketing. Do not restyle `.btn-*` as a prerequisite.

---

## P0 — Control layer (CRM first)

Wrap current CSS where it exists. Product pages gain a React API; pixels stay.

1. Button  
2. IconButton  
3. Checkbox  
4. Radio  
5. Switch  
6. SearchField  
7. Tabs  
8. StatusBadge  
9. Chip  
10. PlatformIcon (only legal new icon import path)  
11. Modal  
12. EmptyState  
13. Pagination  
14. FormField  
15. SemanticSurface (`success` / `warning` / `danger` / `info` / `neutral` / `brand`)

Then: baseline CI ratchets (hex, Tabler, intrinsic button, gradients, rounded) — **lower-only**.

Remove `.app-ui` descendant `border-radius: 0 !important` in favor of radius tokens / surface variant (same P0 slice or immediately after wrappers).

---

## P1 — One DataTable

Blocked on **ADR-044**. Product-facing API: one. Candidates is the canonical implementation. Migration: Vacancies → Leads → Employees → Companies → Admin lists.

---

## P2 — List contract

Search + Filters + Sort + Pagination + Bulk + persisted view state — one contract, different columns. Same ADR-044.

---

## P3 — Layouts / templates

Blocked on **ADR-045**. New modules pick `EntityListPage` / `EntityWorkspace` / `OperationalQueuePage` / `SettingsPage`. They do not design a page type.

---

## Parallel (not this epic’s first slice)

- **ADR-046** Visualization Canon — dashboard category colors vs semantic UI colors.  
- Marketing `surface.public` tokenisation of `#0B0E14` / pipedesign radii — after CRM P0.  
- ADR-038 Actions / Events — different standardization group; may proceed in parallel.

---

## Success bar

A second module that needs a control **adds a catalog ID or reuses one**. It does not copy Tailwind from Candidates or HR.
