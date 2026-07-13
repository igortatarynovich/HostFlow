# Consumer setup flow: от «мне нужен водитель» до сотрудника

**Status:** canonical operating flow (L2) — **обязателен для product, onboarding, intake UI и support**.  
**Setup canon (операционный процесс до READY):** [`canonical-setup-flow.md`](canonical-setup-flow.md) — **читать первым** для onboarding / activation / Health Check.  
**Hierarchy:** L2 workflow canon.  
**Owner:** Product + Recruitment module + Platform (Intake Routing).

**Назначение:** зафиксировать **пользовательский сценарий** настройки и движения **человека** через HostFlow — отдельно от **платформенного канона** (Lead, bindings, decision layer). Документ определяет UX-принципы, которые не должны разъезжаться с архитектурой при росте платформы.

**Связанные документы (не дублировать, а следовать):**

| Документ | Роль |
|----------|------|
| [recruitment-operational-goals-and-order.md](recruitment-operational-goals-and-order.md) | Порядок после convert: Candidate → Handoff → HR |
| [intake-routing-foundation.md](../modules/intake-routing-foundation.md) | Платформенный слой Routing (IntakeSourceProfile, bindings) |
| [recruitment-domain-model.md](../architecture/recruitment-domain-model.md) | Lead / Candidate / Application — платформенная семантика |
| [lead-intake-resolution-and-activity-continuity.md](lead-intake-resolution-and-activity-continuity.md) | Intake Decision Workspace, реактивное создание маршрута |
| [tenant-types.md](../tenant-types.md) | `business_type` (agency / employer / services) |
| [implementation-roadmap-single-tenant-hr-handoff.md](implementation-roadmap-single-tenant-hr-handoff.md) | Handoff → WorkforceEmployee |
| [first-operational-flow-recruitment-documents-hr.md](first-operational-flow-recruitment-documents-hr.md) | Recruitment → Document Hub → HR |
| [people-lifecycle-workflow.md](people-lifecycle-workflow.md) | Поведение после первого контакта — Workspace, блокеры, continuity (**следующий документ после setup**) |
| [hostflow-interaction-architecture.md](../architecture/hostflow-interaction-architecture.md) | **Interaction hub:** List → Workspace → Capabilities → Domain |
| [ADR-017-workspace-layer.md](../architecture/ADR-017-workspace-layer.md) | **Архитектура Workspace Layer** — capability; context; declarations |

---

## 0. Главный принцип HostFlow

> **Пользователь никогда не должен настраивать один и тот же маршрут дважды.**

Это относится ко всем входным точкам:

- Meta Lead Form;
- собственная форма HostFlow;
- Landing;
- WhatsApp;
- Telegram;
- API;
- импорт CSV.

| Раз | Поведение |
|-----|-----------|
| **Первый раз** | Система может спросить: «Куда направлять людей из этого источника?» |
| **Второй раз и далее** | Система использует сохранённый маршрут **автоматически** — без участия человека |

Первый неизвестный источник → оператор выбирает маршрут и ставит «Запомнить» → создаётся routing rule → **режим автопилота**.

Если для второй рекламы с тем же типом источника снова требуется ручная настройка — UX считается сломанным.

---

## 1. Два слоя документации

Этот документ явно разделяет **два языка**:

| Слой | Аудитория | Единица движения | Пример |
|------|-----------|------------------|--------|
| **Пользовательский сценарий** | Администратор, рекрутёр, support | **Человек** | «Мне нужен водитель» → вакансия → люди → сотрудник |
| **Платформенный канон** | Backend, архитектура, интеграции | **Lead** (входящий сигнал) | Ingest → Routing → Decision → Candidate |

**Lead — внутренний объект платформы.** В пользовательской документации, онбординге и Health Check акцент на **движении человека**, не на сущности Lead.

Платформенная цепочка (для архитектуры и кода) — см. §8.

---

## 2. Пользовательский сценарий (главная ось)

Для потребителя HostFlow продукт начинается не с «лида», а с **задачи**:

> «Мне нужен водитель.»

Каноническая пользовательская ось:

```text
Компания → Вакансия → Источник → Люди → Сотрудник → Жизненный цикл сотрудника
```

| Шаг (UI) | Что видит пользователь | Платформенный эквивалент |
|----------|------------------------|--------------------------|
| Компания | Профиль компании, тип бизнеса | Tenant + OwnCompany + onboarding |
| Вакансия | «Driver CE Germany», клиент, условия | Vacancy + CRM Company (client) |
| Источник | Meta Form, Landing, WhatsApp, … | Provider connection + IntakeSourceProfile |
| Люди | Входящие контакты, кандидаты в работе | Lead ingest → Candidate (+ Application) |
| Сотрудник | Передан в HR, карточка сотрудника | Handoff → WorkforceEmployee |
| Жизненный цикл | Документы, контракт, увольнение, … | Employment Lifecycle (см. §7) |

---

## 3. Этапы настройки (пользовательский вид)

Три уровня не смешивать:

| Уровень | Когда | Содержание |
|---------|-------|------------|
| **A. Подготовка компании** | Один раз после покупки | Компания, тип, базовые данные, политика |
| **B. Подготовка вакансии** | На каждое направление найма | Клиент, вакансия, воронка, требования к кандидату |
| **C. Первый человек из источника** | При первом неизвестном источнике | Уточнение маршрута + «Запомнить» |

### Этап A. Подготовка компании (один раз)

1. Создать компанию.
2. Выбрать тип бизнеса:
   - **Агентство** (`business_type=agency`) — нанимаете для клиентов.
   - **Работодатель** (`business_type=employer`) — нанимаете для себя; отдельного «внутреннего клиента» создавать не нужно.
   - **Сервисная компания** (`business_type=services`) — B2B-услуги, не рекрутинг.
3. Заполнить базовые данные.
4. Принять политику (onboarding consent).

**Результат:** компания существует, рекрутинг ещё не настроен.

RODO **не** является отдельным шагом мастера настройки — см. §5.

### Этап B. Подготовка вакансии

1. **Клиент** (только для агентства) — например Poltrakt, MAN Logistics.
2. **Вакансия** — например Driver CE Germany (клиент, должность, страна, условия, статус).
3. **Воронка** (UI: «Этапы отбора») — например Recruitment Driver Poland. Отвечает **только за этапы** канбана.
4. **Требования к кандидату** (UI-термин; платформа: Entity Profile) — например Driver CE EU: документы, поля, проверки, readiness.

На этом этапе источники лидов **ещё не обязательны**.

### Этап C. Источники и маршруты (центр настройки)

Главный экран настройки — **не** вакансия и не интеграция Meta, а **Источники** (платформа: Intake Routing).

Пример UI:

```text
Источники

Meta Form «Drivers Germany»     →  Driver CE Germany  |  Recruitment Driver PL  |  Driver CE EU  |  Anna
Landing «CE Poland»             →  Driver CE Poland   |  Standard Driver        |  Driver CE EU  |  Piotr
WhatsApp                        →  (не настроен)
Telegram                        →  (не настроен)
```

Администратор **не думает** про Binding, Adapter, External Key. Он видит **маршрут**:

- Источник → **Вакансия** → **Воронка** → **Требования к кандидату** → **Ответственный**

Платформенная реализация (bindings, `external_key`) — скрыта за этим экраном. См. [intake-routing-foundation.md](../modules/intake-routing-foundation.md).

### Этап D. Собственная форма (опционально)

Только если рекламируется **форма HostFlow**, а не Meta Lead Form:

- поля, согласия, логика показа;
- публикация → URL;
- URL становится **источником** и появляется в экране «Источники» с тем же маршрутом.

### Этап E. Первый человек → автопилот

```text
Человек пришёл из источника
  │
  ├─ Маршрут известен
  │     → человек попадает в вакансию / к рекрутёру автоматически
  │
  └─ Маршрут неизвестен (первый раз для этого источника)
        → «Получен новый источник. Укажите, куда направлять таких людей.»
        → [Вакансия] [Воронка] [Требования] [Ответственный]
        → [☑ Запомнить для всех следующих]
        → сохраняется маршрут → **автопилот**
```

После «Запомнить» администратор **месяцами** не настраивает тот же источник повторно.

Платформенно: создаётся `IntakeSourceBinding`; disposition `needs_routing` больше не возникает для этого `external_key`.

---

## 4. Routing — центральный объект настройки (UX-канон)

| Было (технический взгляд) | Должно быть (пользовательский взгляд) |
|---------------------------|----------------------------------------|
| Intake Routing Foundation | **Источники** |
| IntakeSourceProfile | **Маршрут источника** (скрытая запись) |
| IntakeSourceBinding | Строка в таблице «Источник → куда» |
| Mapping | Колонки маршрута на экране Источников |
| External key / form_id | Название источника («Meta Form Drivers Germany») |

**Инвариант:** один источник — один маршрут. Изменение маршрута — на экране Источников, не в настройках Meta, не внутри вакансии, не в конструкторе формы.

**Целевой путь в продукте:** Settings → **Источники** (primary), а не Settings → Meta → … → потом искать вакансию.

---

## 5. UI-терминология vs API-терминология

Разделять **язык интерфейса** и **язык платформы**:

| UI (пользователь видит) | API / архитектура (код, спеки) |
|-------------------------|--------------------------------|
| Источники | Intake Routing / `intake_source_profiles` |
| Маршрут | Routing rule (profile + bindings + outcome) |
| Воронка / Этапы отбора | `Funnel` + `FunnelStage` |
| **Требования к кандидату** или **Профиль требований** | **Entity Profile** (`recruitment.candidate.driver_ce`, …) |
| Человек / Кандидат (в рекрутинге) | `Candidate` |
| Заявка на вакансию | `RecruitmentApplication` |
| Входящий контакт (support / debug) | `Lead` |
| Сотрудник | `WorkforceEmployee` |
| RODO / согласие | `Lead.normalized.rodo`, form consents — **не отдельный шаг мастера** |

**Запрещено в UI мастера настройки:** «Выберите Entity Profile» без человекочитаемого названия. Показывать: «Driver CE EU — права, Code 95, медкомиссия, …».

Legacy `CandidateProfile` в UI не продвигать; новые экраны — только через Entity Profile / Профиль требований.

### RODO

- Meta Lead Form — согласие может быть получено в форме Meta → `source_provided`.
- Форма HostFlow — согласие встроено в форму.
- Иные каналы — RODO как **gate на этапе работы с входящим контактом**, не как шаг 6 онбординга.

---

## 6. Health Check — обязательный экран готовности

После настройки (или по запросу) — **один экран «Проверка»**:

| Проверка | Статус |
|----------|--------|
| Компания | ✅ / ⚠️ / ❌ |
| Клиент (если agency) | ✅ / ⚠️ / — |
| Вакансия | ✅ / ⚠️ / ❌ |
| Воронка | ✅ / ⚠️ / ❌ |
| Требования к кандидату | ✅ / ⚠️ / ❌ |
| Источник подключён | ✅ / ⚠️ / ❌ |
| Маршрут настроен | ✅ / ⚠️ / ❌ |
| Тестовый контакт получен | ✅ / ⚠️ / ❌ |
| Кандидат создан | ✅ / ⚠️ / ❌ |

**Все зелёные** → сообщение:

> **Система готова принимать кандидатов.**

Частично зелёные → конкретная подсказка («Подключите Meta», «Укажите маршрут для формы X»). Экран снижает обращения «почему лиды не работают».

Health Check **не заменяет** автопилот; он подтверждает, что цепочка A→B→C пройдена хотя бы один раз.

---

## 7. Полная цепочка человека (включая HR)

Пользовательская ось не заканчивается на «Сотрудник». Зафиксировать **следующий жизненный цикл**:

```text
Входящий контакт
  → Кандидат (рекрутинг)
  → Заявка на вакансию
  → Сбор требований / документов
  → Передача в HR (Handoff)
  → Сотрудник
  → Жизненный цикл сотрудника (Employment Lifecycle)
```

| Этап (UI) | Платформа | Статус продукта |
|-----------|-----------|-----------------|
| Входящий контакт | `Lead` | Работает; в UI — «люди» или intake queue |
| Кандидат | `Candidate` | Requirements Workspace — главный экран рекрутёра |
| Заявка на вакансию | `RecruitmentApplication` | MVP; отделяет dossier от intent |
| Передача в HR | `CandidateHandoff` → accept | Фаза 1 roadmap — Done на стенде |
| Сотрудник | `WorkforceEmployee` + `WorkforceHrCase` | Фаза 1 |
| **Жизненный цикл сотрудника** | Employment Lifecycle | **Зарезервировано архитектурно** — контракт, документы HR, увольнение, возврат; детали — отдельные эпики |

Handoff — **не финал**, а **граница** между Recruitment и HR. HR — начало следующего цикла, не конец продукта.

---

## 8. Платформенный канон (для архитектуры и кода)

Этот раздел — для разработчиков. **Не показывать пользователю как основной сценарий.**

```text
External signal
  → IntakeSourceBinding (adapter: form_id, slug, …)
  → IntakeSourceProfile (route_intent, vacancy hint, entity_profile_code, funnel, assignee)
  → Lead (всегда создаётся на ingest)
  → Decision Layer (duplicate, disposition)
  → Candidate | Client | ServiceOrder | needs_routing
  → RecruitmentApplication (intent)
  → … recruitment ops …
  → Handoff
  → WorkforceEmployee
```

**Жёсткие правила (не нарушать в UX-обёртке):**

| Правило | Смысл |
|---------|--------|
| Lead ≠ Candidate | Входящий сигнал ≠ досье рекрутинга |
| Candidate ≠ Application | Досье ≠ заявка на конкретную вакансию |
| Candidate не создаётся webhook-ом alone | Только conversion decision / outcome executor |
| Маршрут — в Routing | Не в Meta, не в вакансии, не в форме |
| Настроил маршрут один раз | Binding + remember → автопилот |

Подробности: [recruitment-domain-model.md](../architecture/recruitment-domain-model.md), [intake-routing-foundation.md](../modules/intake-routing-foundation.md).

---

## 9. Линейный чеклист для потребителя (agency + Meta, пример)

Пользовательский порядок (без слова «лид»):

1. Компания + тип бизнеса  
2. Клиент  
3. Вакансия  
4. Воронка  
5. Требования к кандидату  
6. Подключить источник (Meta)  
7. Настроить маршрут на экране **Источники**  
8. *(Опционально)* своя форма HostFlow  
9. Запустить рекламу  
10. Первый человек → при необходимости «Запомнить маршрут»  
11. **Health Check** — все ✅  
12. Рекрутёр ведёт кандидата по требованиям  
13. Передача в HR → сотрудник  
14. Жизненный цикл сотрудника  

---

## 10. Технический долг (не менять пользовательский канон)

Следующее — ограничения реализации; UX-канон выше остаётся целевым:

| Долг | Влияние на UX |
|------|----------------|
| Два Meta-роутера (`meta_ads_map` + IntakeSourceProfile) | Риск «настроил в Meta, не в Источниках» — свести к одному экрану |
| Старые спеки candidate-first Meta | Путаница в support — этот документ supersede для consumer flow |
| `CandidateProfile` legacy | UI должен говорить «Требования к кандидату», не legacy config |
| WhatsApp / Telegram не унифицированы | Источники без полного автопилота — довести до IntakeRouter |
| Employment Lifecycle не продуктизирован | Блок в §7 зарезервирован; UI «конец» не на Employee |

---

## 11. Критерии приёмки продукта (product gates)

Любой PR, затрагивающий онбординг, intake или routing, проверять:

1. **Принцип «не настраивать дважды»** — второй контакт с тем же `external_key` не спрашивает маршрут.
2. **Источники — центр** — маршрут редактируется там, не размазан по модулям.
3. **UI без Entity Profile** — в мастерах только «Требования к кандидату» / «Профиль требований».
4. **Пользовательская ось** — документация/help не строят primary flow вокруг Lead.
5. **Health Check** — новый источник или интеграция добавляют пункт проверки.
6. **Цепочка до Employment Lifecycle** — handoff не позиционируется как «конец HostFlow».

---

**Порядок работ:**

```text
consumer-setup-flow-people-to-employee.md (настройка)
  → people-lifecycle-workflow.md (поведение после контакта)
  → UI-спеки Workspace
```

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-07-03 | Initial canon: user journey vs platform layer; Routing as central UI; autopilot; Health Check; Employment Lifecycle hook |
