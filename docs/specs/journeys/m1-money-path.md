# M1 Money Path — путь к первым лидам

**Status:** active (L2 — продуктовый приоритет; не ADR, не Entity Spec).  
**Конституция:** только **фильтр** при решениях; L0 заморожена, L1 достаточен.  
**ADR Search:** только **после** PASS этого пути.

---

## Цель (10–15 минут)

> Человек заходит в HostFlow и через **10–15 минут** получает **ссылку на форму**, которую можно **сразу** использовать в рекламе.

**PASS**, когда выполнены все четыре проверки:

| # | Проверка | PASS когда |
|---|----------|------------|
| 1 | Путь «Создать подбор» | Пользователь проходит flow **до конца** без Settings и без знания G0–G8 |
| 2 | Реклама | После flow есть **готовая ссылка** (и при необходимости QR) для Meta / landing |
| 3 | Первый отклик | Submit формы → **лид/кандидат** в правильной вакансии/подборе, правильный источник |
| 4 | Работа менеджера | Рекрутер открывает workspace и **начинает работу** без доп. настроек (воронка, routing, профиль уже есть) |

Если путь **1–4** не работает — ADR и Entity Spec для Search **не приоритет**.

---

## Целевой путь (как должно быть)

```text
Launchpad
  → «Создать подбор» (1 экран: роль + локация + клиент если agency)
  → «Получить ссылку» (результат: URL + QR + подсказка для Meta)
  → [вне продукта] запуск рекламы
  → первый отклик в «Новые отклики» / очереди работы
  → карточка кандидата с назначенным процессом
```

**Не в пути:** Setup Hub с gates, Entity Profile, Intake Source Binding, отдельный заход в Settings → Lead Forms.

Конституция **не противоречит** этому: Commands (создать подбор), View (новые отклики), Domain владеет state, Workspace без state.

---

## Текущий путь (честно, prod today)

```text
/signup
  → Platform Setup (identity, module, company)     ~5–8 мин
  → Launchpad → Setup Hub (G0–G8 панель)             архитектурный UX
  → [agency] Client                                  ~3 мин
  → Vacancy (title, company, country, …)             ~2 мин
  → Process defaults (funnel + entity profile)       1 click, скрытая магия
  → Intake: «Вручную» ИЛИ Meta                       развилка
       · Manual → Launchpad READY                     ❌ ссылки нет
       · Meta → Settings / Integrations              ❌ не 10 мин
  → Lead Forms                                       только Settings/admin
  → READY = gates PASS                               ≠ «есть ссылка для ads»
```

**E2E сегодня** (`milestone-1-tenant-ready`, slice `full`): manual intake → READY → `/app/candidates`. **Ссылку на форму не проверяет.**

---

## Разрыв (gap)

| Целевое | Сейчас | Критичность |
|---------|--------|-------------|
| Одна команда «Создать подбор» | Client + Vacancy + Process + Intake + gates | блокер |
| Ссылка в конце flow | Lead forms в Settings; после manual — только READY | **блокер денег** |
| «Подбор» в UI | «Вакансия», Setup Hub | UX debt |
| 10–15 мин | 15–25+ мин + Meta OAuth | блокер |
| Менеджер без доп. настроек | Defaults есть, но пользователь не видит связь «ссылка → вакансия» | средний |
| Routing G7/G8 | Backend есть; UI — binding в setup, не в money path | проверить на отклике |

**Технически уже есть:** public intake API, lead forms, vacancy-scoped intake, process defaults, candidate list. **Не собрано** в один денежный сценарий.

---

## Следующая работа (продукт, не спеки)

### Шаг A — пройти глазами (Human / product)

1. Новый tenant, **без** dev-подсказок.  
2. Засечь время до **копируемой ссылки** для ads.  
3. Открыть ссылку в incognito, отправить тестовый отклик.  
4. Найти отклик как рекрутер; зафиксировать friction.

**Wireframe (approved v2):** [`m1-create-search-wireframe.md`](m1-create-search-wireframe.md) — **GO на PR** после prototype gate V0 («пойду в Meta вставить ссылку»).

**Артеfact:** заполненная таблица PASS/FAIL ниже + скриншоты / время.

### Шаг B — минимальный fix (implementation)

Не ждать ADR Search. Итерировать UX поверх **Vacancy** как фасада:

1. **Wizard «Создать подбор»** → сжать client/vacancy/process в короткий flow.  
2. **Финальный экран «Ваша ссылка»** — auto-create/publish lead form + `public/intake?lead_form_slug=…&vacancy_id=…`.  
3. **Intake default = форма**, не manual (manual — secondary).  
4. **Launchpad / workspace entry** → wizard, не Setup Hub gates.  
5. E2E: signup → link on screen → public submit → candidate visible.

Конституционный фильтр на каждый PR: *моделируем работу или экран?* Layer of change: скорее **Workspace + UI**, не Life Cycle.

### Шаг C — после PASS money path

- Entity Spec **Search** + ADR — фиксация **проверенного**.  
- Domain Contract Recruitment — по факту API.  
- Deprecate Setup Hub gates в UX постепенно.

---

## Facilitator checklist (копировать в прогон)

| Step | Действие | Время | PASS | Notes |
|------|----------|-------|------|-------|
| 1 | Регистрация + platform setup | | ☐ | |
| 2 | До **ссылки на форму** без Settings | | ☐ | цель ≤15 мин |
| 3 | Ссылка открывается, форма отправляется | | ☐ | |
| 4 | Отклик виден рекрутеру в ожидаемом месте | | ☐ | |
| 5 | Вакансия/процесс верные | | ☐ | |
| 6 | Можно начать работу (стадия, задача, карточка) | | ☐ | |

**Вопрос понимания (как M1-D9, но про деньги):**

> «Вы запустили рекламу с этой ссылкой. Человек заполнил форму. Что вы делаете дальше в HostFlow?»

PASS — называет конкретный экран/очередь **без** «пойду в настройки».

---

## Что не делаем сейчас

- Новые правила L0 (только если **невозможно** принять решение).  
- ADR Search до PASS таблицы выше.  
- Entity Spec «на опережение».  
- Рефактор nav под конституцию до working link.

---

## Связанные документы

- [`hostflow-constitution.md`](../platform/hostflow-constitution.md) — фильтр  
- [`architecture-decision-framework.md`](../platform/architecture-decision-framework.md) — ADR после практики  
- [`m1-human-gate.md`](../../runbooks/m1-human-gate.md) — текущий gate (gates-heavy; заменить/дополнить money path gate)  
- [`m1-product-contracts.md`](m1-product-contracts.md) — legacy M1 contracts (G0–G8); **не** блокируют money path experiment  
