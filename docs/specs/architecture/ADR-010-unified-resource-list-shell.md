# ADR-010: Единая оболочка списков (Resource List Shell)

**Статус:** Accepted (целевая модель).  
**Область:** SPA (React), все «рабочие» списки сущностей в модулях и на платформе.  
**Phase 2 governance (не giant abstraction):** [`../frontend/entity-table-governance.md`](../frontend/entity-table-governance.md).  
**Родительский стандарт UI:** [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md) (токены, a11y) · [`ADR-043`](ADR-043-ui-component-composition-canon.md) (React kit composition). Product-facing pattern is **`ListWorkspace` + one `DataTable`** ([`ADR-044`](ADR-044-list-workspace-data-presentation-canon.md)); this ADR remains the list-zone / field-kind contract.  
**Связано с:** [`platform-architecture-principles.md`](platform-architecture-principles.md) (модули), [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md), [`pipedesign.md`](../../pipedesign.md) (визуальное направление лендинга).

## Context

Сегодня страницы **кандидатов, компаний, вакансий, сотрудников, заказов** и др. реализованы **разными** композициями: свои тулбары, свои таблицы, свои фильтры, разные паттерны детализации. Это удорожает разработку, ломает ожидания пользователя и мешает вынести общие возможности (колонки, сортировка, сохранённые представления, права).

Нужна **одна нормативная модель**: список = **одна и та же оболочка**, в которую подставляется **конфигурация ресурса** (колонки, фильтры, действия, область данных).

## Decision

### 1. Термины

| Термин | Смысл |
|--------|--------|
| **Resource List** | Экран «много строк одной сущности» в границах модуля/контекста (например `candidates`, `companies`, `vacancies`). |
| **List Shell** | Неизменяемый каркас UI: зоны layout, поведение поиска/сортировки/выбора, модалки/рейлы по правилам ниже. |
| **List Definition** | Данные + метаданные для Shell: идентификатор ресурса, колонки, фильтры, действия строки и массовые, scope API. |
| **Field kind** | Тип **значения** для рендера и фильтрации (не «тип колонки таблицы» в отрыве от домена). |

### 2. Единый layout List Shell (зоны)

Все списки **обязаны** повторять одну сетку регионов (допускается скрытие пустых регионов, не допускается другой порядок без исключения в этом ADR):

1. **Page header** — заголовок ресурса, краткий контекст (tenant/company при необходимости), **одна** primary-действие «Создать …» (если разрешено правами).  
2. **Insights strip (опционально)** — 1 ряд компактных KPI/бейджей **только** если они относятся к **текущему набору фильтров** (как на кандидатах). Без дублирования дашборда.  
3. **Toolbar** — одна строка:  
   - **Глобальный поиск** по ресурсу (один инпут, один контракт debounce + min length).  
   - **Быстрые фильтры** (chips / короткие селекты) — не более **N=5–7** видимых без «Ещё»; остальное в **панели фильтров**.  
   - **Сохранённые представления** (если включены для ресурса).  
   - **Настройка колонок** (иконка) → поповер/рейл: видимость, порядок (drag), сброс.  
   - **Экспорт** (если есть) — вторичное действие.  
4. **Active filters row** — человекочитаемые чипы активных условий + «Сбросить всё».  
5. **Table area** — одна таблица с **единым** визуальным языком строк/хедера (высота строки, hover, selected, empty state).  
6. **Pagination / «показать ещё»** — один паттерн на продукт (сейчас: ниже таблицы, согласовать page size).  
7. **Bulk action bar** — появляется **только** при выборе строк; фиксированная высота, те же кнопки-глифы + текст.  
8. **Detail surface** — см. §5 (рейл vs модалка).

**Запрещено:** дублировать второй «полноценный» тулбар под таблицей с другим набором фильтров без явного режима «Расширенный» (один контракт фильтрации).

### 3. Типизация полей (Field kinds)

Каждая **колонка** и каждый **фильтр** ссылается на **field id** и **kind**. Kind определяет:

- как **рендерить** ячейку;  
- какие **операторы** фильтра допустимы;  
- как **сортировать** (server-side vs client-side — явно в definition).

| Kind | Примеры | Фильтры (минимум) | Сортировка |
|------|---------|-------------------|------------|
| `text` | Название, email | contains, equals, empty | да (лексико) |
| `number` | Сумма, количество | =, range | да |
| `date` | created_at | range, presets | да |
| `datetime` | updated_at | range | да |
| `boolean` | is_archived | да/нет | да |
| `enum` | stage, status | multi-select | да |
| `ref` | company_id → Company | picker / multi | по id или по label через API |
| `user` | manager_id | picker | да |
| `tags` | tags | has any / all | опционально |
| `json` / `custom` | редко | только заранее описанные пути | по умолчанию нет |

Кастомные ячейки (например «пайплайн кандидата») **всё равно** объявляются как колонка с kind `enum` или `custom` + **стабильный** `field_id`, чтобы настройки колонок и права не зависели от JSX-импорта.

### 4. Таблица: колонки, сортировка, видимость

- **Порядок колонок** и **видимость** хранятся в **preferences** пользователя per `(resource_id, optional: scope_key)` (например `candidates` / `candidates:company:123`).  
- **Перетаскивание** — в настройке колонок (не обязательно drag в самом header на v1).  
- **Сортировка** — клик по header там, где `sortable: true` в definition; множественная сортировка — опционально (v2).  
- **Фиксированные колонки** — максимум: первая (обычно «имя / идентификатор») и опционально последняя (действия); остальные скроллятся горизонтально на узких экранах.  
- **Row click** — открывает detail по правилам §5; checkbox — только выбор, не навигация.

### 5. Detail: rail vs modal

| Паттерн | Когда |
|---------|--------|
| **Right rail (drawer)** | Просмотр/редактирование **контекста строки** без смены маршрута; быстрый обзор + основные поля; не блокирует список полностью. |
| **Modal** | Подтверждение, короткая форма **одного шага**, разрушительные действия, выбор из справочника. |
| **Full page** | Сложный многошаговый контур (настройки компании, карточка сотрудника с вкладками) — **после** клика из rail или по прямой ссылке. |

**Правило:** из списка по умолчанию открываем **rail**; переход на full page — явная кнопка «Открыть полностью».

### 6. Меню действий

- **Row actions** — `⋯` в последней колонке; порядок: просмотр → редактирование → разделитель → опасные.  
- **Bulk actions** — только действия, разрешённые для **всех** выбранных строк (или с частичным success — тогда toast с отчётом).  
- Все действия проходят через **permissions** (см. ADR-003 scope); подписи из i18n.

### 7. Данные и API (направление)

**Минимум на v1 (frontend-only definition):** TypeScript-конфиг `listDefinitions[candidates] = { columns, filters, ... }` + общий `ResourceListShell`.

**Цель на v2:** опциональный **List Metadata API** (`GET /api/v1/meta/list-schemas/{resource}`) для колонок/фильтров по роли и плану (сервер отрезает недоступные поля).

Запросы списка остаются **ресурсными** (`/candidates`, `/vacancies`, …); Shell не смешивает модули в один endpoint.

### 8. Миграция (поэтапно)

См. детальный порядок PR14 Phase 2: [`../frontend/entity-table-governance.md`](../frontend/entity-table-governance.md).

1. **Shell only** — layout zones, filter bar, bulk bar, loading/empty/pagination (**без** rewrite list pages).  
2. **`ResourceListShell`** + **`ListDefinition` / `ColumnDef` / `FilterDef`** типы — governance layer, domain cells остаются в модуле.  
3. **Один пилот** — простой список (vacancies / companies / orders), **не** `Candidates.tsx` целиком.  
4. Дальше — migration-by-touch по одному ресурсу.  
5. **Кандидаты** — последний (самый богатый кейс), отдельный slice.  
6. Удалить дублирующие one-off toolbars после паритета.

### 9. Anti-patterns (запрещено)

- **Giant abstraction** — одна таблица со всей бизнес-логикой, колонками и API внутри shell.  
- **Boolean prop explosion** — `compact`, `dense`, `showFilters`, `selectable`, … на shell root; использовать zones, slots, render props, controlled state (см. [`entity-table-governance.md`](../frontend/entity-table-governance.md)).  
- **Bulk «later»** — bulk bar + selection — часть 2A, не отложенная фича.  
- **Big-bang Candidates** — первый PR Phase 2 не мигрирует весь `Candidates.tsx`.  
- **Universal cell renderer** — stage pipeline, doc gates и т.д. остаются domain column renderers.  
- **Второй toolbar** под таблицей (ADR-010 §2).

## Consequences

- Потребуется **рефакторинг** крупных страниц (`Candidates.tsx`, `Companies.tsx`, …) — делать итеративно, не big-bang.  
- Продукт и дизайн обязаны **не вводить** новые «уникальные» списки без обновления ADR-010.  
- Backend может позже отдавать **схему** списка; до тех пор источник правды по колонкам — код фронта + этот документ.

## References

- [`platform-architecture-principles.md`](platform-architecture-principles.md)  
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)  
- [`pipedesign.md`](../../pipedesign.md)  

## История

- **2026-08-13:** Product API bound as `ListWorkspace` + `DataTable` in [`ADR-044`](ADR-044-list-workspace-data-presentation-canon.md); this ADR stays zones / kinds / anti-giant-abstraction.
- **2026-05-20:** §8 пересортирован (shell → pilot → candidates last); §9 anti-patterns; ссылка на `entity-table-governance.md`.
- **2026-05:** первичная фиксация единого List Shell, field kinds, rail/modal, дорожная карта миграции.
