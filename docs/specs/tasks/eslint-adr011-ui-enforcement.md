# Задача: автоматизация чеклиста ADR-011 (ESLint + статические проверки)

**Статус:** В работе — фаза A: скрипт layout `*-[\d]px` **в CI с `--fail`**; база arbitrary layout px вычищена (токены `hf-*` в `tailwind.config.cjs`).  
**Связано с:** [`ADR-011: Платформенный стандарт UI`](../architecture/ADR-011-hostflow-ui-platform-standard.md) (§12 чеклист PR и **политика против дрейфа**, §13 эволюция п.4).

## Цель

Свести ручной чеклист PR к **повторяемым проверкам в CI**, не дублируя уже существующие гейты, и с **поэтапным ужесточением**, чтобы не заблокировать репозиторий тысячами нарушений на первом же включении.

## Уже есть (не дублировать)

| Тема ADR-011 | Существующий артефакт |
|--------------|------------------------|
| Тексты / i18n | `npm run i18n:check`, `npm run i18n:hardcode:check` (`hostflow-frontend/scripts/check-i18n-hardcode.mjs`) |
| Общий lint | `npm run lint` (`hostflow-frontend/eslint.config.js`) |

Остальное из §12 пока **только ручное** — эта задача закрывает пробел.

## Предлагаемый состав работ

### Фаза A — низкий шум, высокая ценность

1. **`eslint-plugin-jsx-a11y`** — **подключено** в `hostflow-frontend/eslint.config.js`: базируется на пресете **`flatConfigs.strict`** (ужесточение относительно `recommended`: полный набор pointer/focus/mouse handlers у **`no-static-element-interactions`**, **`no-noninteractive-tabindex`** без исключений и т.д.); поверх задано **`anchor-is-valid`** с `components: ['Link','NavLink']`, `specialLink: ['to']`. Запуск: `npm run lint`; **входит в `qa:static`** перед `build`. Фокус при открытии модалок/дропдаунов — **`ref` + `useEffect` / `requestAnimationFrame`**, не **`autoFocus`**.
2. **Кастомное правило или скрипт** на запрет очевидных нарушений §3:
   - **Сделано:** `hostflow-frontend/scripts/check-adr011-ui-patterns.mjs` — layout/sizing префиксы (`m*`, `p*`, `gap*`, `space-*`, `w*`, `h*`, `min-*`, `max-*`, `size`, `rounded*`, `top`/`right`/`bottom`/`left`/`inset*`) с `-[Npx]`; `text-[Npx]` не трогаем. Команда: `npm run ui:adr011:check` (**`--fail`**). Входит в `npm run qa:static`; отчёт: `adr011-ui-patterns-report.json` (в `.gitignore`). Повторяющиеся размеры — токены **`hf-<px>`** в `tailwind.config.cjs` (`spacing` / `maxWidth` / `minWidth` / `maxHeight`).
   - **Исключения:** подавление строкой с `adr011-allow` / `adr011-ignore` или предыдущей строкой.
   - Опционально далее: raw hex в `className` (высокий шум).
3. Документировать **исключения**: комментарий `/* adr011-allow: arbitrary spacing */` или единый `allowlist` файл, если без этого нельзя (редкие макеты) — частично покрыто подавлением в скрипте.

### Фаза B — средний риск ложных срабатываний

4. Правила/скрипты на **паттерны кнопок и полей** (§6–7): **частично** — `scripts/report-adr011-button-patterns.mjs`: **`ui:adr011:buttons:report`** / **`ui:adr011:buttons:check`** (ratchet, `scripts/adr011-button-baseline.json`); в **`qa:static`** после `ui:adr011:dates:check`. Подавление: `adr011-button-ignore` на строке. **Поля (§7):** `scripts/report-adr011-field-patterns.mjs` — **`ui:adr011:fields:report`** / **`ui:adr011:fields:check`** (`--fail`, ratchet `scripts/adr011-field-baseline.json` → `maxMissingFieldOpens`); в **`qa:static`** после кнопок; подавление: `adr011-field-ignore`.
5. **Даты** (§9): **`npm run ui:adr011:check`** не покрывает даты. **Сделано:** `scripts/report-adr011-date-patterns.mjs` — считает строки с `.toLocaleString(`, `.toLocaleDateString(`, `.toLocaleTimeString(` в `src` (известные хелперы `dateFormat.ts`, `documentUtils.ts` исключаются из «gate»-счётчика). **`npm run ui:adr011:dates:report`** — только отчёт (exit 0). **`npm run ui:adr011:dates:check`** — **`--fail`**, если число попаданий **>** `scripts/adr011-date-baseline.json` → `maxNonHelperHits` (ратчет). **Входит в `qa:static`** после `lint` через **`ui:adr011:dates:check`**. Подавление строки: `adr011-date-ignore`.

### Фаза C — интеграция в CI

6. ~~Новый npm-скрипт~~ — **`ui:adr011:check`** с `--fail`, в `qa:static`.
7. ~~Report-only~~ — включён **strict fail** после вычистки базы layout `px`.

## Критерии приёмки

- [x] В `hostflow-frontend` есть команда `ui:adr011:check` (layout arbitrary `px`, **`--fail`** в CI).
- [x] `eslint-plugin-jsx-a11y` в ESLint (пресет **`strict`** + кастом **`anchor-is-valid`** для Router).
- [x] В ADR-011 §13 п.4 — ссылка на эту задачу.
- [x] В [`ci_gates.md`](../quality/ci_gates.md) — актуализировано описание гейта.
- [x] CI: `qa:static` падает при новых layout arbitrary `px` (регрессия ADR-011 §3).

## Заметки по реализации

- Плоский ESLint regexp по всему файлу хуже, чем **AST** (`typescript-eslint` + `no-restricted-syntax` с селектором на `JSXAttribute[name.name='className']`) для точности.
- Альтернатива: отдельный Node-скрипт по образцу `check-i18n-hardcode.mjs` — проще внедрить, проще игнорировать папки.
- Списки сущностей (ADR-010) автоматически не проверить полностью — оставить ручным пунктом или отдельный линтер на импорт оболочки списка (отложено за рамки фазы A).

## История

- **2026-05-06:** задача заведена как отдельная итерация после ADR-011.
- **2026-05-06:** добавлен `check-adr011-ui-patterns.mjs`, `npm run ui:adr011:check`, шаг в `qa:static`.
- **2026-05-07:** база arbitrary layout `px` сведена к нулю; токены `hf-*` в `tailwind.config.cjs`; `ui:adr011:check` с `--fail`.
- **2026-05-07:** `eslint-plugin-jsx-a11y` + правки разметки (region/link/button roles); `npm run lint` без новых jsx-a11y ошибок при текущем baseline.
- **2026-05-07:** исправлены ошибки React Compiler / hooks (`purity`, `preserve-manual-memoization`, `static-components`, `no-extra-boolean-cast`); pipeline drag registry — `eslint-disable` для `react-hooks/refs`; **`npm run lint` в `qa:static`**.
- **2026-05-07:** Tailwind **`z-hf-*`** + замена основных `z-[n]`; **`ui:adr011:dates:report`** (фаза B §9, report-only).  
- **2026-05-07:** **`text-hf-h1|h2|h3`** + `.app-ui` в `components.css`; **`ui:adr011:dates:report`** в **`qa:static`**.
- **2026-05-07:** jsx-a11y **`media-has-caption`** снова активно (recommended); **`ui:adr011:buttons:report`** + шаг в **`qa:static`** (§6–7, report-only).
- **2026-05-07:** отчёт кнопок переведён на **TypeScript AST**; **`html-has-lang`** без override (recommended).
- **2026-05-07:** jsx-a11y **`anchor-is-valid`** с `Link`/`NavLink` + `to`; **`click-events-have-key-events`** и **`mouse-events-have-key-events`** включены; хелпер `src/utils/a11yClick.ts` + правки кликабельных `div`/`label` (модалки, календарь, контекстные меню, документы).
- **2026-05-07:** jsx-a11y **`no-static-element-interactions`** и **`no-noninteractive-element-interactions`** снова из recommended (убраны overrides): `role="presentation"` для оверлеев/оболочек, `role="button"` + `tabIndex` + `aria-label` для кликабельных ячеек календаря, разделение backdrop/dialog в модалках, Ctrl/Cmd+Enter на инвойсе через обёртку `role="presentation"` + `ref` на `<form>`.
- **2026-05-07:** jsx-a11y **`label-has-associated-control`** без override: `htmlFor`/`id`, для подписей рядом с чекбоксом — `<label>` только с текстом (инпут соседом); для «голых» чекбоксов в списках — `aria-label` на `<label>`.
- **2026-05-07:** jsx-a11y **`interactive-supports-focus`** без override (recommended, `tabbable` как в плагине); текущая база `npm run lint` без новых нарушений.
- **2026-05-07:** jsx-a11y **`no-autofocus`** без override: все бывшие `autoFocus` заменены на программный фокус (`ref` + эффект) в селектах, модалках, онбординге, глобальном поиске.
- **2026-05-07:** базовый набор jsx-a11y переведён с **`recommended`** на **`strict`**; доработки: `role="presentation"` на hovercard-портале и DnD-обёртке карточки, drag&drop аватара вынесен с `<label>` на обёртку `presentation`.
- **2026-05-08:** ADR-011 §9 — **`ui:adr011:dates:check`** (`--fail` + `scripts/adr011-date-baseline.json` ratchet) в **`qa:static`** вместо report-only.
- **2026-05-08:** ADR-011 §6–7 — **`ui:adr011:buttons:check`** (`--fail` + `scripts/adr011-button-baseline.json` ratchet) в **`qa:static`**.
- **2026-05-08:** ADR-011 §7 — **`ui:adr011:fields:report`** / **`ui:adr011:fields:check`** (ratchet `scripts/adr011-field-baseline.json`) в **`qa:static`**.
