# Entity table governance (Phase 2 — PR14)

**Status:** canonical (frontend L2) — aligns with [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md) visual sign-off; product API is [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md)  
**ADR:** [`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md) (`ListWorkspace` + `DataTable`), [`ADR-010`](../architecture/ADR-010-unified-resource-list-shell.md) (zones / field kinds), [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md) (UI platform standard)  
**Task:** [`../tasks/ui-consistency-foundation.md`](../tasks/ui-consistency-foundation.md) Phase 2  
**Code target:** `hostflow-frontend/src/components/surfaces/` — **`EntityListShell`** (2A), demo **`/app/dev/entity-list-shell`**; no production list migration until 2B.

## Principle: governance layer, not giant abstraction

`ListWorkspace` / `DataTable` — **один** платформенный механизм на все operational lists ([`ADR-044`](../architecture/ADR-044-list-workspace-data-presentation-canon.md)). Это не «у каждого модуля своя таблица» и не мега-компонент, который знает колонки кандидата.

Типичная ошибка design-system веток: один компонент с **бизнес-ячейками, API и actions внутри** — ломает домены. Правильно: один API, `ListDefinition` + domain cell slots снаружи.

### Shared (platform canon)

| Область | Что унифицируем |
|---------|-----------------|
| **Shell layout** | Зоны ADR-010 §2 (header → toolbar → active filters → table → pagination → bulk bar) |
| **Interaction model** | Row click → rail/modal rules; checkbox ≠ navigation; debounced search; sort header contract |
| **Spacing / chrome** | `.table`, `.crm-page-inset`, filter chips, bulk bar height, ADR-011 tokens |
| **Filter / action canon** | Один toolbar; active filter row; primary create в header; export secondary |
| **Row states** | hover, selected, disabled, focus — не per-page Tailwind |
| **Loading / empty / error** | Один набор паттернов для Entity lists |
| **Bulk actions** | Bar появляется только при selection; фиксированная высота |
| **Pagination** | Один продуктовый паттерн (page size, labels, placement) |

### Domain-specific (остаётся в модуле)

| Область | Не выносить в generic table |
|---------|------------------------------|
| **Columns** | Набор, порядок, visibility — `ListDefinition` per resource |
| **Density** | Compact vs comfortable — per resource flag, не глобальный default |
| **Business cells** | Stage pipeline, doc %, HR badges — render props / column `cell` slots |
| **Contextual row actions** | Меню строки зависит от entity + permissions + stage |
| **Insights strip** | KPI только где нужны (candidates), не в shell по умолчанию |
| **API / filters** | Endpoint, query shape, field kinds — definition layer |

**Правило:** shell принимает **slots / definition**, не знает бизнес-правил кандидата или HR.

## API shape: composition, not boolean explosion (Phase 2A anti-pattern)

Shell **не** должен превращаться в monster component через десятки boolean props. Это первый признак неправильной abstraction — через 2–3 PR shell станет новым legacy-монолитом.

### Запрещено на shell root

```tsx
// ❌ Anti-pattern — не допускать
<EntityListShell
  compact
  dense
  sticky
  selectable
  highlightWarnings
  showFilters
  showInlineActions
  showBulkBar
  ...
/>
```

Каждый новый флаг = combinatorial UX debt и невозможность ревью.

### Правильно: zones + slots + controlled state

| Механизм | Для чего |
|----------|----------|
| **Composition** | `EntityListShell` = layout frame; дети/слоты заполняют зоны |
| **Named slots / zones** | `header`, `toolbar`, `activeFilters`, `table`, `pagination`, `bulkBar` — ADR-010 §2 |
| **Render props** | `renderToolbar`, `renderBulkActions`, `renderEmpty` — domain передаёт контент, не флаги |
| **Controlled state** | `selection`, `sort`, `filters`, `pagination` — state в list page / hook; shell отображает |
| **`ListDefinition`** | Колонки, field kinds, row actions — data/config, не props shell |

**Правило ревью:** если PR добавляет boolean prop на shell — отклонять, предложить slot или render prop.

### Density / compact

Не `compact={true}` на shell. Варианты:

- `ListDefinition.density?: 'comfortable' | 'compact'` (per resource), или  
- CSS class на table zone из definition, или  
- отдельный thin wrapper `EntityListShellCompact` только если реально нужны два frame (редко).

## Bulk actions: day-one interaction model (не «потом»)

Bulk operations — то, что делает HostFlow **рабочим CRM**, а не admin UI. **Обязательны в Phase 2A**, не откладываются на 2B.

### Canonical bulk contract (2A deliverable)

| Поведение | Canon |
|-----------|--------|
| Visibility | Bulk bar **только** при `selection.length > 0` |
| Placement | Sticky над pagination или под table (один продуктовый выбор — зафиксировать в 2A PR) |
| Height | Фиксированная; не прыгает layout |
| Actions | Slot `bulkBar` / `renderBulkActions(selection)` — domain передаёт кнопки |
| Selection | Controlled: `selectedIds` + `onSelectionChange`; header checkbox = select page |
| Clear | «Clear selection» в bulk bar |
| Permissions | Domain фильтрует actions; shell не знает «can_delete_candidate» |

2A **без** рабочего bulk bar + selection chrome = Phase 2A **не принят**, даже если layout красивый.

Smoke для 2A (demo route / fixture list):

- [x] Select 1 row → bulk bar appears  
- [x] Select all on page → bulk bar updates count  
- [x] Clear selection → bulk bar hides  
- [x] Bulk bar не перекрывает pagination (bulk между table-scroll и pagination; 2026-05-20)

## PR14 Phase 2A–2B merge gate (2026-05-20)

| Gate | Status |
|------|--------|
| Demo smoke passed (`/dev/entity-list-shell`, DEV) | ✅ |
| Vacancies list behavior unchanged (API / params / sort / bulk handlers) | ✅ |
| No boolean prop explosion on `EntityListShell` | ✅ |
| No business cells inside shell | ✅ |
| `Candidates.tsx` not touched | ✅ |
| Bulk bar does not cover pagination | ✅ |

**2B pilot:** `VacancyList.tsx` only. **Next (2C):** Companies or Orders touch-by-touch; **Candidates last**, separate small PR.

## Phase 2 delivery order (обязательный)

Не начинать с миграции **`Candidates.tsx` целиком**. Таблицы — главный operational surface CRM; ошибка здесь дороже всего.

```text
Phase 2A — Shell only (no list page rewrite)
  ├── Zones API: slots / render props / controlled state (NO boolean prop explosion)
  ├── List shell layout (ADR-010 zones)
  ├── Selection + sticky bulk action bar (day-one — not deferred)
  ├── Filter bar + active filter chips
  ├── Loading / empty / error states
  └── Pagination canon

Phase 2B — One pilot surface (touch-migrate)
  └── Простой список: Vacancies OR Companies OR Orders (не Candidates)

Phase 2C — Iteration
  ├── Следующий список только migration-by-touch
  └── Candidates — последний, отдельный epic slice (богатый кейс)
```

**Запрещено в Phase 2A–2B:**

- Big-bang rewrite `Candidates.tsx`
- «Универсальная колонка» с бизнес-логикой внутри shell
- Второй toolbar под таблицей
- Новый список без ADR-010 / этого canon

## Relationship to Phase 1 (documents)

Phase 1 закрыл **document row / blocker** presentation. Phase 2 не смешивает document rows в Entity table — документы в списках сущностей остаются **business cells**; `DocumentRow` используется в rail/panel/dossier, не как замена всех table cells.

## Agent / PR rules (Phase 2)

1. Новый entity list → оболочка shell + `ListDefinition`; не копировать toolbar из соседней страницы.  
2. PR меняет **один** list page в Phase 2B, не три.  
3. Колонки и actions — в definition файле модуля, не в shell source.  
4. См. `.cursor/rules/hostflow-ui-surfaces.mdc` — migration-by-touch.

## Sign-off (Phase 2)

| Gate | When |
|------|------|
| Phase 0–1 visual parity | Before any Phase 2 code |
| Shell demo page or Storybook-less smoke route | End of 2A |
| Pilot list parity screenshot | End of 2B |

## References

- [`ADR-044-list-workspace-data-presentation-canon.md`](../architecture/ADR-044-list-workspace-data-presentation-canon.md) (`ListWorkspace` + `DataTable`)
- [`ADR-010-unified-resource-list-shell.md`](../architecture/ADR-010-unified-resource-list-shell.md)  
- [`../tasks/ui-consistency-foundation.md`](../tasks/ui-consistency-foundation.md) §2  
- [`ADR-011`](../architecture/ADR-011-hostflow-ui-platform-standard.md)
