# UI Component Canon — catalog

**Hierarchy:** L2 — closed component ID catalog + consumption rules; **not** a visual restyle SoT  
**Decision record:** [`ADR-043`](../architecture/ADR-043-ui-component-composition-canon.md)  
**Parent model:** [`ADR-038`](../architecture/ADR-038-platform-standardization-model.md) · [`platform-standardization-model.md`](platform-standardization-model.md) (area `design_interaction`)  
**Visual / a11y / tokens:** [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md) (amended by ADR-043: CSS is implementation)  
**List shell (target):** [`ADR-010`](../architecture/ADR-010-unified-resource-list-shell.md) — bound as Data layer in **ADR-044**  
**Owner:** Frontend platform  
**Epic:** [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md)

---

## 1. Purpose

Index of canonical HostFlow UI families. Product modules **compose** these IDs. Local recreation of an existing ID is an architecture violation.

This file does **not** lock pixel values, Figma, or chart palettes (ADR-046). It does **not** extract DataTable (ADR-044) or page templates (ADR-045).

---

## 2. Consumption contract

| Allowed in product pages (target) | Forbidden in new product-page code once the family has a kit component |
|-----------------------------------|------------------------------------------------------------------------|
| `<Button variant="primary">` | `className="btn-primary"` as the public API |
| `<PlatformIcon id="…">` | new `@tabler/icons-react` imports outside the registry |
| `<StatusBadge semantic="danger">` | ad-hoc `bg-rose-100` pills for status meaning |
| `<SemanticSurface tone="warning">` | page-local gradients / `rounded-2xl` heroes |
| `<DataTable>` (after ADR-044) | new hand-written operational `<table>` |

CSS classes `.btn-*`, `.input`, `.table` remain **implementation** inside `hostflow-frontend/src/styles/components.css` and kit wrappers.

Import surface (target): primitives/composites from `hostflow-frontend/src/components/ui/`; Icon from `hostflow-frontend/src/platform/icons/`. Additional layout/template roots are named in ADR-045.

---

## 3. Surface profiles

| Profile | Code signal (today) | Token intent |
|---------|---------------------|--------------|
| `surface.crm` | operational SPA under `.app-ui` | dense; radius via `--radius-control` / `--radius-surface` — **not** descendant `!important` |
| `surface.public` | marketing / public / auth | more open; same Foundation color/type/spacing |

Do not mix profiles on one screen without an explicit contract (ADR-011 §2 still holds).

---

## 4. Catalog

Row contract: `component_id` · `layer` · `status` · `runtime_today` · `notes`.

`status`: `exists` (kit component usable) · `wrap` (CSS/legacy exists; React API is the P0 job) · `gap` (no canonical control yet).

### Foundation

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `Color` | exists | `FOUNDATION_V1` + `brand.*` | Semantic UI colors only. Chart categories → ADR-046 |
| `Type` | exists | `FOUNDATION_V1` + `.app-ui` h1–h3 | Two type scales (CRM vs pipedesign) collapse into surface profiles, not a second Foundation |
| `Spacing` | exists | `FOUNDATION_V1` 0–8 | — |
| `Radius` | wrap | Tailwind + illegal `.app-ui !important` | Replace override with tokens (epic) |
| `Shadow` | exists | `FOUNDATION_V1` | — |
| `Motion` | gap | ad-hoc transitions | No motion canon in this PR |

### Primitive

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `Button` | wrap | `Button.tsx` + `.btn-*`; product pages use CSS | Public API = React; CSS inside |
| `IconButton` | wrap | `variant="icon"` on Button + `.btn-icon` | Require accessible name |
| `Input` | wrap | CSS `.input` only (INPUT_V1) | React wrapper allowed now that composition canon requires a kit API — does not reopen INPUT_V1 pixel debate |
| `Textarea` | wrap | `.textarea` | Same as Input |
| `Select` | wrap | `Combobox` / `MultiCombobox` + native `<select className="input">` | SELECT_V1 scenario tree still applies |
| `Checkbox` | gap | native + `accent-color` | P0 |
| `Radio` | gap | native | P0 |
| `Switch` | gap | none | P0 |
| `Badge` | wrap | `StatusBadge` + `.badge` + inline pills | Status meaning → StatusBadge only |
| `Chip` | exists | `Chip.tsx` (3 consumers) | Promote usage; no fifth behavior without PR |
| `Icon` | wrap | `PlatformIcon` unused; Tabler direct | Registry is the only new-import path |

### Composite

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `SearchField` | gap | per-list inputs | P0 control; list contract in ADR-044 |
| `FilterBar` | gap | Candidates / dashboard / pipeline one-offs | Was FILTER_BAR_V1 — now this ID |
| `FormField` | wrap | dead `controls/Field.tsx` | Label + hint + error; replace `text-red-600` |
| `Tabs` | wrap | `.tabs` / `.tab` CSS | P0 React |
| `Modal` | wrap | `components/Modal.tsx` | Close control must be IconButton; MODAL_V1 not a separate canon |
| `Dropdown` | wrap | `.dropdown` CSS | — |
| `Pagination` | gap | mixed | P0 + ADR-044 policy |
| `EmptyState` | wrap | `EmptyStatePanel` local classes | P0 |
| `Toast` | wrap | `Toast.tsx` | — |
| `DateField` | wrap | native `input type=date` | INPUT_V1 native until DateField ships |
| `SemanticSurface` | gap | HR gradients / heroes | P0 expressiveness for ready/attention/blocked |

### Data

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `DataTable` | wrap | four parallel implementations | **One** product API — ADR-044; Candidates = canonical implementation |
| `TableHeader` | wrap | candidates header | ADR-044 |
| `SortControl` | wrap | candidates / companies | ADR-044 |
| `FacetFilter` | wrap | `FacetFilterMenu` | ADR-044 |
| `BulkActionBar` | wrap | `EntityListBulkBar` | ADR-044 |

### Layout

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `PageHeader` | exists | ~64 pages | Best-adopted layout |
| `ListLayout` | wrap | ADR-010 zones; EntityListShell barely used | ADR-045 |
| `EntityWorkspace` | wrap | `platform/entity-workspace` + candidate card | Was ENTITY_LAYOUT_V1 — ADR-045 |
| `SettingsLayout` | wrap | `.settings-*` CSS | ADR-045 |
| `SplitPane` | gap | rails / inspectors | ADR-045 |

### Template

| component_id | status | runtime_today | notes |
|--------------|--------|---------------|-------|
| `EntityListPage` | gap | each list composes itself | ADR-045; new modules pick a template |
| `EntityDetailPage` | gap | candidate card is benchmark only | ADR-045 |
| `SettingsPage` | wrap | settings shells | ADR-045 |
| `OperationalQueuePage` | gap | inbox / HR queue / leads | ADR-045 |

---

## 5. Child artifacts (no longer independent canons)

| Former program | Becomes |
|----------------|---------|
| `FOUNDATION_V1` | Foundation layer of this catalog |
| `PRIMITIVES_V1` / `BUTTON_V1` / `INPUT_V1` / `SELECT_V1` / `CHIP_V1` / `STATUS_BADGE_V1` | Primitive IDs |
| `TABLE_V1` | Data layer → ADR-044 |
| `FILTER_BAR_V1` (unstarted) | `FilterBar` |
| `ENTITY_LAYOUT_V1` (draft) | `EntityWorkspace` → ADR-045 |
| REF-UI-000 roadmap | Execution notes under this tree |

Do not open a new `*_V1` as a sibling canon. Extend this catalog.

---

## 6. History

- 2026-08-13: Initial catalog under ADR-043. Runtime wrappers, DataTable extraction, layouts, visualization, and CI ratchet deferred to the epic / ADR-044…046.
