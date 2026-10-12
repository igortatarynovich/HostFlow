# Task: UI System Foundation Pass

**Status:** In progress — Phases A–D shell cutovers landed on this line; remaining candidate-rail migrate-on-touch and HR field-row polish stay open  
**ADR:** [`ADR-011-hostflow-ui-platform-standard.md`](../architecture/ADR-011-hostflow-ui-platform-standard.md) §13  
**Frontend canon:** [`FOUNDATION_V1.md`](../frontend/FOUNDATION_V1.md), [`PRIMITIVES_V1.md`](../frontend/PRIMITIVES_V1.md), [`REF-UI-000-ui-standardization-roadmap.md`](../frontend/REF-UI-000-ui-standardization-roadmap.md)  
**North star:** [`HOSTFLOW_UX_NORTH_STAR.md`](../frontend/HOSTFLOW_UX_NORTH_STAR.md)

## Question answered

> Как довести Candidate Card до эталонной Entity Workspace **без** создания feature-local UI language, и в какой последовательности безопасно переносить тот же язык на HR и остальные workspace?

## Constraint (from ADR-011 §13)

**No feature-local UI language.**

Любая страница HostFlow собирается из:

1. **Tokens / primitives** — spacing, typography, control heights, radius, border, surface, text / semantic colors, shadows, focus / hover / disabled; Button, Input, Select, Checkbox, Badge / Chip, IconButton, Avatar, Divider.  
2. **System components** — Tabs, Section / Card, FieldRow, FieldGrid, InlineEditField, StatusBadge, ActionMenu, StagePipeline, SidebarWidget, ProgressWidget, FilterBar, DataTable, EmptyState, Alert, PageHeader / EntityHeader, EntityContextBar, DocumentRequirementRow (`hostflow-frontend/src/components/ui/`).  
3. **Page patterns** — entity workspace, list / table workspace, operational queue, dashboard, settings / configuration.

Feature / module владеет данными, composition и business behavior. Размеры, цвета, borders, spacing, tabs, cards, form controls, badges, tables и navigation patterns — только у системы.

Если элемента нет — он создаётся как system component. Если system component не даёт утверждённый UX — меняется он, а не локальная копия под Candidate / HR.

**Запрещён** слепой глобальный редизайн заменой CSS-классов по SPA. Старые экраны рассчитаны на старые размеры.

Этот task **не** переоткрывает lock `FOUNDATION_V1` / `PRIMITIVES_V1` / `TABLE_V1`. Concern отделён от requirement-resolution; не смешивать в одном PR.

## Acceptance criterion (Candidate Card reference)

После завершения Candidate Card:

- визуальный результат соответствует эталонной композиции Entity Workspace (header → context / status → stage pipeline → tabs → main + persistent sidebar);
- **ни один** визуальный паттерн, созданный ради этого результата, не принадлежит Candidate Card;
- Candidate Card — только композиция общесистемных HostFlow UI primitives / components / patterns и business-specific content.

Preserve operational baseline ([`HOSTFLOW_UX_NORTH_STAR.md`](../frontend/HOSTFLOW_UX_NORTH_STAR.md)): карточка остаётся production benchmark. Меняется **владение** визуалом — паттерн принадлежит системе, страница только композирует его. `Preserve` не разрешает оставить feature-local CSS.

## Safe sequence

1. Зафиксировать ограничение в ADR-011 §13 и этот task (**done** при merge этого документа).  
2. Довести Candidate Card до эталона **только** системными компонентами (не новый локальный визуал, не массовая замена классов по SPA).  
3. Проверить: на Candidate Card нет feature-local visual primitives (инвентарь ниже → 0).  
4. Documents / Profile / Legalization закрыть только через system components (например двухколоночный layout → `FieldGrid`; document row → `DocumentRequirementRow`; «Обязательно» → semantic `StatusBadge`).  
5. Аудит HR против тех же page patterns (контрпримеры уже известны; полный audit — отдельный шаг).  
6. Миграция HR **page-by-page**, отдельные PR: Employee Card → Employees list → ZUS → Dashboard.  
7. **STOP перед шагом 6:** этот foundation pass **не** включает код HR. HR не «подкрашивается» и не получает HR design system.

## Inventory — Candidate Card local visual primitives (must leave the feature)

Системный слой уже частично используется: `StagePipeline`, `StatusBadge`, `Button`, `WorkspaceSection`, `WorkspaceWidget`, `WorkspaceTabs` (через chrome).

| Item | Location | Problem | Target | Status |
|------|----------|---------|--------|--------|
| `ReadRows` | was in `CandidateCardChrome.tsx` | Local field-row layout beside `InlineFieldRow` / `FieldGrid` | `components/ui/ReadFieldRows.tsx` | Done |
| Edit / Done control in `CardAccordion` | `CandidateCardChrome.tsx` | Raw `<button className="text-xs …">` | `Button` variant `link` | Done |
| `text-[11px]` meta / captions | `CandidateDocsWorkspacePanel`, `CandidateTimelinePanel`, `CandidateProcessControls` | Outside `FOUNDATION_V1` body scale (`type-body-xs` = `text-xs`) | `text-xs` + system `Button` where interactive | Done (named files) |
| Remaining `text-[11px]` / local badges | other `components/candidate/**` rails / checklists | Still feature-local | Migrate on touch via system `StatusBadge` / `Button` / `text-xs` | Open |

Доработка system components (если UX эталона требует): расширять `FieldGrid`, `DocumentRequirementRow`, `StatusBadge`, `EntitySummaryHeader` и соседние `components/ui/*` — не дублировать в `components/candidate/**`.

## Inventory — HR as counter-example (out of scope this pass)

| Item | Location | Problem |
|------|----------|---------|
| Local status colors | `hostflow-frontend/src/components/hr/EmployeeRecordHeader.tsx` (`statusBadgeClass`) | Bypasses `StatusBadge` |
| Local progress pills | `hostflow-frontend/src/components/hr/HrVerificationProgressBadge.tsx` | Own pill + `text-[11px]` |
| Entity shell | Employee Card pages | Separate large card + employment stepper + own tabs / forms / widgets instead of Entity Workspace pattern |

Целевая композиция Employee Card (после отдельной миграции): EntityHeader → context / status → StagePipeline → Tabs → main workspace + persistent sidebar — тот же pattern, что Candidate Card, с HR-данными.

Целевые page patterns для остальных HR surfaces (после отдельной миграции):

- Employees list — Page header → metrics → FilterBar → DataTable  
- ZUS — Page header → status metrics → FilterBar → action / composer → DataTable / Queue  
- Dashboard — Page header → MetricCards → operational sections / queues  

## Explicit non-goals

- Blind SPA-wide Button / Input / Card class replacement  
- New module design systems (Recruitment, Documents, HR)  
- Reopening `FOUNDATION_V1` / `PRIMITIVES_V1` / `TABLE_V1` locks  
- Mixing with requirement-resolution contract work in the same PR  
- Full delete of every `text-[11px]` outside Phase A tab surfaces  

## Checklist

- [x] ADR-011 §13 records No feature-local UI language  
- [x] This task records acceptance + sequence + inventories  
- [x] Named Candidate Card inventory items → system (`ReadFieldRows`, `CardAccordion`/`Button`, three panels `text-xs`)  
- [x] Phase A: Profile/Documents/Legalization — `FieldGrid` wrappers, `StatusBadge` for requirement status, upload `Button`, `requirementRowStatusToSemantic`  
- [x] Phase B: Employee Card → `EntitySummaryHeader` / `StagePipeline` / `WorkspaceTabs` / `WorkspaceWidget`; dead `EmployeeRecordHeader` removed  
- [x] Phase C: Employees list → `PageHeader` / metrics `StatusBadge` / `FilterBar` / table; verification badge uses system `StatusBadge`  
- [x] Phase D: ZUS → `PageHeader` / `FilterBar` / `WorkspaceSection` queue; sticky gradient removed  
- [ ] Remaining candidate rails `text-[11px]` — migrate-on-touch only  
- [ ] Employee Card field rows → `FieldGrid` / `ReadFieldRows` on touch  
