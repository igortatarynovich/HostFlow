# ADR-043: UI Component & Composition Canon

**Status:** Accepted  
**Date:** 2026-08-13  
**Layer of change:** Experience (Design & Interaction) | Composition rule + component catalog  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md) · [`ADR-010`](ADR-010-unified-resource-list-shell.md) · [`ADR-038`](ADR-038-platform-standardization-model.md) · [`ADR-046`](ADR-046-analytics-visualization-canon.md) · L2 [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md) · epic [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md)

**Amends (does not supersede):** ADR-011 — visual tokens, a11y, dates, i18n, and PR drift policy remain in force. This ADR changes the **consumption contract**: product modules compose React kit APIs; CSS/Tailwind is implementation inside the kit.

**L0 checklist:** No new L0 P-rule; no new capability Passport (UI Platform Standard already exists as shared capability #11). Applies P-01 / P-03 / INV-05 / INV-07 and AGENTS Rule 4 (two-module promotion) to **UI patterns**. Does not rewrite Passport/Manifest shape.

---

## Context

HostFlow already has a design **canon** (FOUNDATION_V1, PRIMITIVES_V1, TABLE_V1, ADR-011 CSS classes). It does **not** yet have a platform **UI system**: product pages still decide buttons, tables, search, icons, radius, and semantic colors locally.

The gap is no longer documentation volume. Parallel `*_V1` specs without a composition rule let every module keep a private UI language. CSS class names (`btn-primary`) cannot be the public API of the design system — they do not give a single place to change HostFlow a year from now.

ADR-038 area 13 already forbids local semantic colors and primitive clones. This ADR makes that rule **operational**: a closed component catalog, a React consumption contract, a two-module promotion rule for UI, and a ratchet (not a rewrite).

---

## Decision

### 1. One chain — pages compose, they do not invent

```text
Foundation tokens → Primitives → Composites → Layouts → Page Templates → Product pages
```

A product page **must not** decide how a button, input, checkbox, icon, search, sort, filter bar, table, tabs, modal, radius, warning/rejected/ready color, gradient, list layout, or entity card is built.

A product page **assembles** catalogued HostFlow controls and passes them data.

**Platform law:**

> Product modules MUST compose UI from canonical HostFlow controls, composites, layouts and templates. Local recreation of an existing platform pattern is prohibited.

If a UI pattern is needed by a **second independent module**, it leaves the module and becomes part of the HostFlow UI Platform (same two-module rule as domain rules). Default: keep inside module only while a single owner uses it **and** no catalog equivalent exists.

### 2. Public API is React — CSS is implementation

| Layer | Role |
|-------|------|
| **Public API** | React components + layout/template contracts (stable `component_id`) |
| **Implementation** | `components.css`, Tailwind, tokens in `tailwind.config.cjs` |

Target consumption:

```tsx
<Button variant="primary">Save</Button>
```

not `className="btn-primary"` in product modules.

Existing `.btn-*`, `.input`, `.table` **may wrap inside** kit components. Visual restyle is **not** required to lock this ADR.

**Legacy:** `className="btn-primary"` remains valid until the control-layer ratchet covers that file (migrate-on-touch). **New** product-page code after the P0 kit lands must use the React API for any catalogued family that already has a component.

`components.css` must not be treated as the design system. It is the implementation layer of the kit.

### 3. Surface profiles — one Foundation, two surfaces

CRM and Marketing are **two surfaces of one brand**, not two design systems.

| Profile | Intent |
|---------|--------|
| `surface.crm` | Denser, squarer operational UI |
| `surface.public` | More open marketing / public / auth chrome |

Hex, radius, type, and spacing **must not** appear as page-local accidents (`#0B0E14`, `#3FA3A8`, ad-hoc `rounded-2xl`). They come from Foundation tokens applied through the active surface profile.

Do **not** make CRM and Marketing visually identical.

### 4. Radius is a token — kill global `!important`

`.app-ui *:not([class*='rounded-full']) { border-radius: 0 !important; }` is **prohibited going forward**. It breaks the component contract (Button claims `rounded-xl`, the shell secretly forbids it).

If CRM must stay square, that is `--hf-radius-control` / `--hf-radius-surface` (or a surface variant) owned by the kit — not a descendant override. P0 runtime removed the `!important` rule and introduced the tokens.

### 5. Semantic expression is allowed — local invention is not

HR (and any module) may highlight ready / attention / blocked. They **must not** invent gradients, `rounded-2xl` heroes, or private palettes.

Catalog family: `SemanticSurface` with platform tones (`success` | `warning` | `danger` | `info` | `neutral` | `brand`). Color, border, icon, and background belong to the platform.

Dashboard **categorical** colors are **not** Foundation semantic colors. They belong to **[ADR-046](ADR-046-analytics-visualization-canon.md)** (Analytics, Visualization & Reporting Canon): three color spaces, meaning→family, story composition, Analytics View / presentation mode. Map stage/status → semantic type first (`rejected` → `danger`), never a page-owned `#f97316`.

### 6. Closed catalog (IDs)

Stable `component_id` families live in L2 [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md). Layers:

| Layer | Families (closed for this ADR) |
|-------|--------------------------------|
| **Foundation** | Color, Type, Spacing, Radius, Shadow, Motion |
| **Primitive** | Button, IconButton, Input, Textarea, Select, Checkbox, Radio, Switch, Badge, Chip, Icon |
| **Composite** | SearchField, FilterBar, FormField, Tabs, Modal, Dropdown, Pagination, EmptyState, Toast, DateField, SemanticSurface |
| **Data** | DataTable, TableHeader, SortControl, FacetFilter, BulkActionBar |
| **Layout** | PageHeader, ListWorkspace, EntityWorkspace, SettingsLayout, SplitPane |
| **Template** | EntityListPage, EntityDetailPage, SettingsPage, OperationalQueuePage |

Extending the closed set requires a dedicated platform PR (Platform-first). REF-UI `*_V1` artifacts become **children of this tree**, not independent canons.

Existing primitives (`Button`, `StatusBadge`, `Chip`, `Combobox`, `PageHeader`, `Modal`, `PlatformIcon`) are **adopted into** these IDs; they are not a second kit.

### 7. One product-facing DataTable (bound in ADR-044)

Four parallel tables (`.table` CSS, `layout/DataTable`, `DataTableEngine`, hand-written `<table>`) are architectural debt.

**Decision:** there will be **one** product-facing DataTable API, hosted by **`ListWorkspace`**. Engine/helpers/schema may exist underneath. Pages must not choose among engines.

Canon: [`ADR-044`](ADR-044-list-workspace-data-presentation-canon.md). **Candidates / TABLE_V1** is the capability bar. Page cutover is epic P1–P2.

### 8. Work order (runtime epic — not more specs)

Do **not** start with marketing. The dangerous split is inside CRM.

| Priority | Scope |
|----------|--------|
| **P0** | Control layer: Button, IconButton, Checkbox, Radio, Switch, SearchField, Tabs, StatusBadge, Chip, PlatformIcon, Modal, EmptyState, Pagination, FormField — wrap current CSS where it exists |
| **P1** | One `ListWorkspace` + `DataTable` public API (ADR-044) |
| **P2** | Search + Filters + Sort + Pagination + Bulk + persisted view state — same pattern |
| **P3** | Layouts / templates: EntityListPage, EntityWorkspace, OperationalQueuePage, SettingsPage |

Follow-on ADRs (same tree):

- ~~**ADR-044** — List Workspace & Data Presentation~~ **Done** — [`ADR-044`](ADR-044-list-workspace-data-presentation-canon.md)
- **ADR-045** — Layout & Page Template Canon
- ~~**ADR-046** — Visualization Canon~~ **Done** — [`ADR-046`](ADR-046-analytics-visualization-canon.md) (analytics + reporting language; Recruitment efficiency = reference)

### 9. Enforcement — ratchet, not rewrite

Documentation without CI will drift again. After P0 components exist, CI ratchets **new** violations against a baseline:

- no new raw hex outside allow-listed files;
- no new `@tabler/icons-react` imports outside the icon registry;
- no new intrinsic `<button>` in product pages (use `Button` / `IconButton`);
- no new hand-written `<table>` in product pages (use `DataTable`);
- no new gradients outside visualization / marketing allow-list;
- no new `rounded-*` outside kit implementation;
- no new local control when a catalog equivalent exists.

**Do not** rewrite all legacy first. Freeze today’s counts; each PR may only lower them. The ADR itself was docs-only; P0 runtime (`npm run ui:kit:check`) lives in the composition epic.

### 10. Runtime of this ADR document

The ADR PR did **not** migrate product pages or extract DataTable. P0 follow-on (same epic): kit wrappers, radius tokens, removal of `.app-ui` descendant `!important`, and the lower-only CI ratchet.

---

## Out of scope (explicit)

- Visual restyle of `.btn-*` / brand palette
- Marketing pixel-parity with CRM
- Shipping ADR-045 in this PR
- Big-bang Tabler / hex / table cleanup
- New L0 P-rule or UI capability Passport
- Actions / Events vocabulary (ADR-038 areas 9–10)

---

## Explicit next

1. Epic P1–P2 — `ListWorkspace` runtime extract ([`ADR-044`](ADR-044-list-workspace-data-presentation-canon.md)).
2. **ADR-045** Layout & Page Template Canon.
3. Events vocabulary may proceed **in parallel**.

---

## Architecture Review Checklist (L0)

- [x] P-01…P-05 respected — composes existing UI Platform capability; no new Passport
- [x] INV-05 — CSS/Tailwind inside the kit is not the public API
- [x] INV-07 / two-module rule — second consumer promotes the pattern to platform
- [x] ADR-011 not superseded; consumption contract amended
- [x] L0 freeze untouched
- [x] Area 13 Design & Interaction filled with a composition canon (analytics language: ADR-046)

---

## Consequences

- Positive: UI follows the same Platform-first rule as entities, types, relationships, and vocabulary; modules stop growing private UI languages; a year-later visual change has one kit surface.
- Negative: until P1–P3 ship, legacy className and parallel tables remain legal under migrate-on-touch.
- Follow-on: ListWorkspace runtime (ADR-044 epic P1–P2) → layouts (045). Analytics + reporting language: [`ADR-046`](ADR-046-analytics-visualization-canon.md).

---

## Alternatives considered

1. **More `*_V1` specs without a composition ADR** — rejected; that is the current failure mode.
2. **Treat `components.css` as the public design system** — rejected; class names cannot be versioned or swapped as a kit.
3. **One visual language for CRM and Marketing** — rejected; two surface profiles, one Foundation.
4. **Big-bang rewrite of all pages in this PR** — rejected; ratchet + migrate-on-touch.
5. **Fold this into ADR-011 rewrite** — rejected; ADR-011 stays visual/a11y/token law; composition is a separate platform rule (same split as Field ≠ DataType).

---

## Cross-references (updated in same change set)

- [`../platform/ui-component-canon.md`](../platform/ui-component-canon.md) — L2 catalog
- [`ADR-044-list-workspace-data-presentation-canon.md`](ADR-044-list-workspace-data-presentation-canon.md) — ListWorkspace + DataTable
- [`ADR-046-analytics-visualization-canon.md`](ADR-046-analytics-visualization-canon.md) — analytics + presentation/sharing language
- [`../tasks/ui-platform-composition-epic.md`](../tasks/ui-platform-composition-epic.md) — P0–P4 epic
- [`ADR-011-hostflow-ui-platform-standard.md`](ADR-011-hostflow-ui-platform-standard.md) — amended consumption
- [`ADR-038-platform-standardization-model.md`](ADR-038-platform-standardization-model.md) · [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md)
- [`architecture-guide.md`](architecture-guide.md) · [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) · [`platform-architecture-principles.md`](platform-architecture-principles.md)
- [`../frontend/REF-UI-000-ui-standardization-roadmap.md`](../frontend/REF-UI-000-ui-standardization-roadmap.md)
