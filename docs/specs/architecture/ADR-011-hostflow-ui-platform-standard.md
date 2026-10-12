# ADR-011: Платформенный стандарт UI HostFlow (всё, что можно стандартизировать)

**Статус:** Accepted (целевая модель + фиксация текущей имплементации).  
**Область:** HostFlow SPA (`hostflow-frontend`), публичные формы/порталы на том же стеке; маркетинговые страницы — в рамках той же **палитры и типографики**, но с отдельными layout-правилами.  
**Связано с:** [`ADR-010`](ADR-010-unified-resource-list-shell.md) (профиль списков), [`pipedesign.md`](../../pipedesign.md) (визуальное направление лендинга), [`pipe.md`](../../pipe.md) (продуктовый blueprint). Операторский Acquisition SPA: [`../frontend/ACQUISITION_MARKETING_IA_V1.md`](../frontend/ACQUISITION_MARKETING_IA_V1.md) (зоны и disclosure; без новых примитивов).

## 1. Иерархия источников правды

| Уровень | Файл / артефакт | Роль |
|---------|-----------------|------|
| **Гovernance** | Этот ADR | Что обязано быть едино, запреты, исключения, эволюция. |
| **Визуальное направление** | [`pipedesign.md`](../../pipedesign.md) | B2B-тон, сетка 8px, базовые цвета, типографические уровни, карточки лендинга. |
| **Токены в коде** | `hostflow-frontend/tailwind.config.cjs` | `brand.*`, `fontFamily.sans`, расширения `borderRadius` / `boxShadow`. |
| **Компонентный слой** | `hostflow-frontend/src/styles/components.css` | `.btn*`, `.input`, `.table`, `.card`, `.app-ui`, `.settings-*`, `.crm-*`, модалки. |
| **Списки** | ADR-010 | Единая оболочка списков поверх этого ADR. |

**Правило:** новые экраны **не вводят** параллельные системы отступов, шрифтов, скруглений и кнопок без обновления таблицы в §7 и без правок в `components.css` / `tailwind.config.cjs`.

## 2. Две поверхности продукта (важно)

В коде уже заложено разделение:

1. **Маркетинг / «мягкий» UI** — классы `.card`, `.btn`, `.input` с **скруглением** (`rounded-xl`), ближе к цифрам в [`pipedesign.md`](../../pipedesign.md) (кнопка 12px radius → в Tailwind обычно `rounded-xl` 0.75rem).  
2. **CRM / основное приложение** — контейнер **`.app-ui`**: глобально **квадратные углы** у потомков (см. комментарий в `components.css`), плотная структура, отдельные правила для таблиц и полей.

**Нельзя** смешивать на одном экране без явного контракта: либо область в `.app-ui`, либо вне его (портал, публичная анкета). Исключения документировать в PR.

## 3. Сетка, отступы, ширина

| Тема | Стандарт |
|------|----------|
| **Базовая сетка** | Кратно **8px** (как в pipedesign); в Tailwind предпочитать `p-4`, `gap-4`, `space-y-4` и т.д. |
| **Контент страницы** | `.page-content`: `max-w-6xl mx-auto`; настройки: `.settings-page-shell` / `settings-page-shell-narrow` (`max-w-4xl`). |
| **CRM inset** | `.crm-page-inset` + `.crm-page-stack` — единые отступы от края main и вертикальный ритм блоков. |
| **Full-bleed** | Только осознанно (`crm-workspace-fill` + отсутствие лишних обёрток). |
| **Именованные размеры** | Повторяющиеся layout-значения в px — токены **`hf-<число>`** в `tailwind.config.cjs` (rem = px÷16), классы `min-w-hf-720`, `max-w-hf-1600` и т.д.; CI: `npm run ui:adr011:check`. |
| **Z-index стек** | Токены **`z-hf-*`** в `theme.extend.zIndex` (`hf-dropdown`, `hf-overlay`, `hf-nav`, `hf-modal`, `hf-toast`, `hf-rail-modal`, …); избегать произвольных `z-[9999]` в новом UI. |
| **Заголовки CRM** | Токены **`text-hf-h1`**, **`text-hf-h2`**, **`text-hf-h3`** (`theme.extend.fontSize`) — соответствуют уровням в `.app-ui`; для кастомных заголовков вне `h1–h3` использовать те же классы. |

**Запрещено:** произвольные `px-[13px]`, `mt-[17px]` в новых страницах — только токены или согласованное расширение темы.

## 4. Типографика

| Элемент | CRM (`.app-ui`) | Маркетинг / общее |
|---------|-----------------|-------------------|
| Шрифт | `font-sans` → **Inter** (+ fallback в `tailwind.config.cjs`) | То же |
| Заголовки страницы | `h1`–`h3` заданы в `components.css` для `.app-ui` | Уровни H1–H3 из pipedesign для лендинга |
| Основной текст | `text-sm` / `leading-5`, вторичный `text-slate-600` | Body / Small из pipedesign где уместно |

## 5. Цвета

- **Бренд:** шкала `brand.50`–`brand.900` в `tailwind.config.cjs`, выровнена с pipedesign (`500` ≈ primary `#3FA3A8`, `700` ≈ accent `#2E6F74`).  
- **Семантика:** успех / ошибка / инфо — через `.alert-*` и согласованные `emerald` / `rose` / `cyan` (не вводить новый «красный» оттенок для той же роли).  
- **Текст:** `slate-900` / `slate-600` / `slate-500` для иерархии, не произвольный `gray-*` в одном экране.

## 6. Кнопки, ссылки, иконки

| Вариант | Класс | Когда |
|---------|-------|--------|
| Основное действие | `.btn-primary` | Один primary на логический блок. |
| Вторичное | `.btn-secondary` | Отмена, «Назад», вторичный CTA. |
| Разрушительное | `.btn-danger` | Удаление, необратимые действия. |
| Компакт | `.btn-sm` / `.btn-xs` | Тулбары, таблицы (с сохранением `min-h` на touch). |
| Иконка | `.btn-icon` | Только с `aria-label` / tooltip. |

**Модалки:** класс `.modal-surface` задаёт минимальную высоту касания для кнопок и полей на mobile.

## 7. Поля ввода, формы, настройки

| Элемент | Стандарт |
|---------|----------|
| Лейбл | `.label` |
| Текст / select / textarea | `.input` / `.textarea` (вне `.app-ui`) или правила `.app-ui :where(input…)` внутри CRM |
| Группировка | `.settings-panel`, `.settings-toolbar`, `.settings-page-shell` |
| Валидация | Единый тон: `border-rose`, текст ошибки `text-sm text-rose-700`, не произвольные цвета |

**Вложенность:** внутри настроек не более **трёх** визуальных уровней (страница → панель → секция); глубже — вкладки или отдельная страница.

## 8. Таблицы, меню, модалки, рейлы

| Паттерн | Стандарт |
|---------|----------|
| Таблица списков | `.table` в `components.css` (отступы ячеек, hover, шапка); внутри `.app-ui` — дополнительные `:where(table)` правила. |
| Выпадающее меню | `.dropdown` / `.dropdown-item` или компонент, визуально совместимый с ними. |
| Модалка | Общий контейнер с `.modal-surface`, фокус-ловушка и ESC — единый компонент/хук по мере выноса. |
| Rail / drawer | Один компонент (ширина, overlay, анимация); см. ADR-010 §5. |

## 9. Даты, время, числа

| Тема | Стандарт |
|------|----------|
| Хранение / API | **ISO 8601** в UTC, unless домен требует иного (явно в спеке сущности). |
| Отображение | Форматирование через **locale** пользователя / workspace (`Intl`, общие хелперы в `src/`). |
| Относительное время | Один хелпер («2 дня назад») для лент и списков. |
| Часовой пояс | Явно в настройках tenant/company где нужно; не смешивать silent UTC и local в одной колонке без подписи. |

## 10. Языки (i18n)

- Обязательные локали продукта — см. `docs/specs/i18n/index.md` и правила в `docs/specs/core.md`.  
- **Запрещено** в новых компонентах: пользовательские строки только в JSX без ключей `t('…')` / аналога.  
- Формат плюралов и подстановок — единый стиль ключей (`app.<area>.<screen>.<element>`).

## 11. Доступность и плотность

- Интерактивные цели **не уже 44×44px** на touch-контурe где это уже задано в `components.css` — сохранять.  
- Фокус: видимое кольцо `focus:ring-*` в стиле brand, не `outline-none` без замены.  
- Иконки-кнопки: обязательный доступное имя.  
- Статический контроль: `eslint-plugin-jsx-a11y` в `hostflow-frontend/eslint.config.js` (пресет **`strict`**, плюс **`anchor-is-valid`** с `Link`/`NavLink`); полный прогон — `npm run lint` (см. задачу [`eslint-adr011-ui-enforcement.md`](../tasks/eslint-adr011-ui-enforcement.md)).

## 12. Чеклист для PR (новый UI)

- [ ] Нет «магических» пикселей вне темы / `components.css`.  
- [ ] Кнопки только из системы `.btn*`.  
- [ ] Поля — `.input` / CRM-правила `.app-ui`.  
- [ ] Страница в правильной оболочке (`.app-ui` vs маркетинг).  
- [ ] Тексты через i18n.  
- [ ] Даты через общие хелперы.  
- [ ] Списки сущностей — согласование с ADR-010 (или явный tech debt с задачей).  
- [ ] Нет **нового дрейфа** от этого ADR; любые отступления задокументированы (см. политику ниже).

### Политика против дрейфа (обязательно на ревью)

Цель — не плодить вторую «систему» UI поверх §1–§10. **Полный рефактор старых экранов не требуется в каждом PR**; требование — не усугублять хаос и по возможности подтягивать код в зоне изменений.

1. **Запрещено без явного согласования в описании PR** вводить параллельные: сетку отступов / ширин, набор классов для кнопок и полей вместо `.btn*` и `.input` (и CRM-правил `.app-ui`), оболочки списков вразрез с ADR-010, пользовательские строки вместо i18n в новом коде.  
2. **Допустимое отступление** только с явной пометкой: в PR — кратко *почему* и *как погасим* (ссылка на задачу tech debt **или** обновление этого ADR и токенов в `tailwind.config.cjs` / `components.css`). В коде, где работает автоматическая проверка, допускается комментарий с `adr011-allow` / `adr011-ignore` (см. `npm run ui:adr011:check`).  
3. **Зона изменений:** ревьюер по возможности просит убрать дрейф в затронутых фрагментах или завести follow-up; не блокировать фичу из‑за несвязанного legacy в том же файле — но **не принимать** новый дрейф под видом «как было рядом».

## 13. No feature-local UI language

**Правило:** любая страница HostFlow собирается из единой системы tokens / primitives, system components и page patterns. Feature или module задаёт данные, composition и business behavior. Ему не принадлежат размеры, цвета, borders, spacing, tabs, cards, form controls, badges, tables или navigation patterns.

Три уровня (сверху вниз владение идёт у платформы, не у модуля):

| Уровень | Что входит | Где живёт |
|---------|------------|-----------|
| **1. Tokens / primitives** | Spacing, typography, control heights, radius, border, surface, text colors, semantic colors, shadows, focus / hover / disabled; затем Button, Input, Select, Checkbox, Badge / Chip, IconButton, Avatar, Divider | `FOUNDATION_V1`, `PRIMITIVES_V1`, `tailwind.config.cjs`, `components.css`, `hostflow-frontend/src/components/ui/` |
| **2. System components** | Tabs, Section / Card, FieldRow, FieldGrid, InlineEditField, StatusBadge, ActionMenu, StagePipeline, SidebarWidget, ProgressWidget, FilterBar, DataTable, EmptyState, Alert, PageHeader / EntityHeader, EntityContextBar, DocumentRequirementRow | `hostflow-frontend/src/components/ui/` (+ layout shells по ADR-010) |
| **3. Page patterns** | Entity workspace, list / table workspace, operational queue, dashboard, settings / configuration | Композиция из уровня 2; Candidate Card — reference implementation Entity Workspace |

**Обязательные следствия:**

1. Если необходимого UI-элемента нет — он создаётся как **reusable system component** (уровень 1 или 2).  
2. Если существующий system component не позволяет получить утверждённый UX — **изменяется сам system component**, а не создаётся локальная копия для Candidate / HR / Documents / Recruitment.  
3. Запрещены feature-local `h-[31px]`, произвольные `text-[11px]`, сырые `#...`, свои border / radius / tab / card / badge / table shells непосредственно в module pages.  
4. **Запрещён** глобальный редизайн слепой заменой CSS-классов по всему SPA. Сначала reference page (Candidate Card) доводится до эталона через system components; затем страницы мигрируют последовательно. Массовая замена `Button` / `Input` / `Card` без page-by-page cutover ломает legacy composition.  
5. Documents / Profile / Legalization и последующий HR cutover закрываются **только** через уровни 1–3. Модуль не получает отдельный design system.

Acceptance и безопасная последовательность — implementation note: [`../tasks/ui-system-foundation-pass.md`](../tasks/ui-system-foundation-pass.md). Allow-list токенов и primitives (`FOUNDATION_V1`, `PRIMITIVES_V1`, `TABLE_V1`) этим разделом **не переоткрываются**.

Дополнение к чеклисту §12 для нового UI:

- [ ] Нет feature-local visual primitives: новый визуальный паттерн либо уже system, либо добавлен в `components/ui` / токены в том же PR.  
- [ ] Нет слепой массовой замены классов вне зоны reference / текущей page migration.

## 14. Эволюция

1. Свести разрозненные страницы к **одному** набору layout-классов (`.crm-page-inset`, `.settings-page-shell`, …).  
2. Расширить `tailwind.config.cjs` недостающими токенами (~~z-index шкала~~ — `z-hf-*`; ~~типографика H1–H3 приложения~~ — `fontSize.hf-h1|hf-h2|hf-h3`, используются в `.app-ui :where(h1–h3)` в `components.css`).  
3. Вынести модалку / drawer в **один** React-компонент с тестами.  
4. Подключить **lint** на запрещённые паттерны (например raw hex в className) — отдельная инженерная задача: [`eslint-adr011-ui-enforcement.md`](../tasks/eslint-adr011-ui-enforcement.md). Уже в репозитории: `npm run ui:adr011:check` в `hostflow-frontend` (layout arbitrary `px`, **`--fail`** в CI через `qa:static`); повторяющиеся размеры — токены **`hf-*`** в `tailwind.config.cjs`.  
5. System UI foundation pass — Candidate Card как reference Entity Workspace без feature-local visual ownership; затем page-by-page cutover (HR и др.): [`../tasks/ui-system-foundation-pass.md`](../tasks/ui-system-foundation-pass.md).

## References

- [`ADR-010-unified-resource-list-shell.md`](ADR-010-unified-resource-list-shell.md)  
- [`pipedesign.md`](../../pipedesign.md)  
- [`../frontend/ACQUISITION_MARKETING_IA_V1.md`](../frontend/ACQUISITION_MARKETING_IA_V1.md)  
- [`../frontend/FOUNDATION_V1.md`](../frontend/FOUNDATION_V1.md)  
- [`../frontend/PRIMITIVES_V1.md`](../frontend/PRIMITIVES_V1.md)  
- [`../tasks/ui-system-foundation-pass.md`](../tasks/ui-system-foundation-pass.md)  
- `hostflow-frontend/tailwind.config.cjs`  
- `hostflow-frontend/src/styles/components.css`  

## История

- **2026-10-12:** §13 — **No feature-local UI language** (три уровня tokens → system components → page patterns; запрет локальной копии и слепой замены классов); §14 — эволюция (бывший §13); task [`ui-system-foundation-pass.md`](../tasks/ui-system-foundation-pass.md).  
- **2026-05:** первичная фиксация платформенного UI-стандарта (токены, две поверхности, формы, таблицы, i18n, даты, чеклист).  
- **2026-05:** §12 — политика против дрейфа для ревью и отдельный пункт чеклиста.  
- **2026-05:** CI — `ui:adr011:check --fail`; база layout arbitrary `px` вычищена, токены `hf-*`.  
- **2026-05:** §11 — `eslint-plugin-jsx-a11y` в `eslint.config.js`.  
- **2026-05:** `npm run lint` (в т.ч. jsx-a11y + React Compiler rules) в **`qa:static`** / CI.  
- **2026-05:** Токены **`z-hf-*`** в Tailwind; **`text-hf-h1|h2|h3`** в Tailwind; `.app-ui` заголовки через эти токены.
- **2026-05:** §9 даты — `ui:adr011:dates:report` / ratchet **`ui:adr011:dates:check`** в **`qa:static`** (`scripts/adr011-date-baseline.json`).
- **2026-05:** §6–7 кнопки — `ui:adr011:buttons:report` / ratchet **`ui:adr011:buttons:check`** в **`qa:static`** (TypeScript AST, `scripts/adr011-button-baseline.json`); jsx-a11y `media-has-caption` без отключения; **`html-has-lang`** из recommended.
- **2026-05:** §7 поля — **`ui:adr011:fields:report`** / ratchet **`ui:adr011:fields:check`** в **`qa:static`** (`scripts/adr011-field-baseline.json`).
- **2026-05:** jsx-a11y **`anchor-is-valid`** (Router `to`) + **click/mouse + keyboard** на неинтерактивных элементах; утилита `a11yClick.ts`.
- **2026-05:** jsx-a11y **`no-static-element-interactions`** и **`no-noninteractive-element-interactions`** без override: интерактивные поверхности с явной ролью/лейблом или `role="presentation"` для чисто визуальных слоёв.
- **2026-05:** jsx-a11y **`label-has-associated-control`** без override (`htmlFor`/`id`, разделение label/чекбокс где нужно).
- **2026-05:** jsx-a11y **`interactive-supports-focus`** из recommended без override.
- **2026-05:** jsx-a11y **`no-autofocus`** из recommended; первичный фокус через `ref`/эффекты вместо `autoFocus`.
- **2026-05:** jsx-a11y пресет **`strict`** (вместо `recommended`) + точечные правки разметки под расширенные правила.
