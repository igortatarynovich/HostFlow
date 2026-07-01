# IA v2 — `PageHeader` («breadcrumb + 1 CTA»)

**Статус:** active.
**Источник доктрины:** `docs/HOSTFLOW_AUDIT_AND_PLAN.md` §2.1 (принцип «один экран — одна цель», §2.2 «Видимый следующий шаг»), Phase 1 #6 + Phase 1 IA v2.
**Реализация:** `hostflow-frontend/src/components/nav/PageHeader.tsx`,
`hostflow-frontend/src/components/nav/PageBreadcrumb.tsx`,
`hostflow-frontend/src/nav/breadcrumbRegistry.ts`.

---

## Контракт

Каждая операционная страница CRM рендерит **ровно один** `<PageHeader>` в верхней части основного контента. Header даёт пользователю две вещи в одной строке:

1. **«Где я?»** — иерархический breadcrumb из `BREADCRUMB_REGISTRY` (`Home › Section › Subsection › Current`). Permission-gated родители деградируют до plain-текста.
2. **«Что мне сделать сейчас?»** — единственная primary-кнопка (CTA) справа. Verb-noun копи (`+ Добавить вакансию`, `+ Запросить документы`, `Отправить сообщение`).

Под breadcrumb-строкой опционально — `title` и `subtitle`. Их следует использовать только если breadcrumb-leaf не достаточно информативен (детальные страницы, dynamic context).

### Запрещено

- Дублировать «глобальную» полосу вроде legacy `CrmContourWayfindingStrip` (удалена в Phase 1 #6).
- Ставить более одной primary-кнопки в header. Если требуется несколько действий — одно primary, остальные `secondaryActions` (визуально secondary-стиль).
- Выводить header без CTA, если страница не помечена `kind="browse"` явно (см. ниже).

### Опт-аут: browse-страницы

Read-only / list-landing страницы, где primary-CTA живёт на каждой строке таблицы (например `/app/calendar`, `/app/inbox/*` страницы со списком тредов, `/app/automations/log`), могут опустить `primaryAction`, но **обязаны** передать `kind="browse"`. Это:

- документирует намерение;
- позволяет тестам/линтерам не считать их регрессией;
- сигнализирует ревью, что отсутствие CTA — осознанное решение.

---

## API

```tsx
import { PageHeader } from '../components/nav/PageHeader'

<PageHeader
  primaryAction={
    <button type="button" className="btn-primary" onClick={openAddModal}>
      + Добавить вакансию
    </button>
  }
/>
```

Все пропы:

| Prop | Type | Когда использовать |
|------|------|-------------------|
| `primaryAction` | `ReactNode` | **Required для `kind="action"`**. Одна `<button>` или `<Link>` с `className="btn-primary"`. |
| `secondaryActions` | `ReactNode` | 0–3 secondary-кнопок (filter toggle, view switch, refresh). Слева от primary. |
| `title` | `ReactNode` | Если breadcrumb-leaf не информативен (carduyellow detail, dynamic name). |
| `subtitle` | `ReactNode` | Один short hint строки. Не описание модуля. |
| `breadcrumbItems` | `PageBreadcrumbItem[]` | Полностью кастомный trail (для нестандартных URL-shape). |
| `breadcrumbCurrentLabel` | `string` | Override leaf-label, оставляя авто-trail родителей. |
| `hideHome` | `boolean` | Скрыть `Home` иконку (только для onboarding/auth). |
| `kind` | `'action' \| 'browse'` | По умолчанию `'action'`. `'browse'` — опт-аут для list-landing страниц. |

---

## Расположение в layout

```tsx
return (
  <div className="space-y-4">
    <PageHeader primaryAction={...} />
    {/* page body */}
  </div>
)
```

- **Без** wrapping `<section>` или фоновой плашки — header «лёгкий» и сам по себе.
- В страницах со sticky toolbar (например `Candidates.tsx` где список с виртуализацией) header идёт **до** sticky-полосы.
- Settings drill-down страницы используют **`SettingsSubpageHeader`** (`hostflow-frontend/src/components/settings/SettingsSubpageHeader.tsx`), а не `PageHeader` — чтобы сохранить «back» ссылку в settings-хабе.

---

## Аудит покрытия

На момент закрытия IA v2 (Phase 1 + Phase 2 audit):

| Группа страниц | Стратегия CTA |
|----------------|---------------|
| `/app/candidates`, `/app/leads`, `/app/companies`, `/app/clients`, `/app/vacancies`, `/app/services` | Action — primary CTA «+ Add …» / «Open work panel». |
| `/app/dashboard`, `/app/work` | Action — primary CTA = «следующий NBA / fix in one click» (см. §2.2 audit-плана). |
| `/app/calendar`, `/app/inbox/*` thread-список, `/app/automations/log`, `/app/communications/sla-incidents`, `/app/team-availability` | Browse — `kind="browse"`. CTA на отдельных строках/тредах. |
| `/app/profile`, `/app/my-availability` | Action — primary CTA = «Сохранить» из верхнего fixed-bar (form save). |
| `/app/automations/*`, `/app/integrations` hubs | Action — primary CTA = «+ Создать правило / Подключить интеграцию». |
| Settings drill-down (`/app/settings/**`) | Используется `SettingsSubpageHeader` (back + title + actions), не `PageHeader`. |
| Detail pages (`/app/leads/:id`, `/app/candidates/:id`, `/app/invoices/:id`, etc) | Action — primary CTA = «следующее действие на сущности» (e.g. «Перевести на этап», «Подписать», «Запросить документы»). |
| `/app/onboarding/*` | Action — primary CTA = «Continue» wizard step. |

Финальный гейт «у каждой `kind="action"` страницы есть `primaryAction`» — будущая lint-проверка через AST-сканер; на данный момент enforce-ится через ревью.

---

## Why this works

1. **Одна когнитивная точка:** пользователь, открыв любую страницу, видит сразу два фокусных элемента — где он и что делать. Никаких глобальных контурных полос, дублирующих сайдбар.
2. **Predictable layout:** primary-CTA всегда в правом верхнем углу основного контента — как у Linear, Pipedrive, Asana.
3. **Permission-aware:** breadcrumb-родители деградируют до plain-текста, если у пользователя нет доступа к разделу. Primary-action сама проверяет `canEdit`/`permission` (page-side).
4. **Тестируемость:** контракт `kind` + единое имя компонента позволяет в будущем подключить ESLint-rule «`PageHeader` должен иметь `primaryAction` или `kind="browse"`».
