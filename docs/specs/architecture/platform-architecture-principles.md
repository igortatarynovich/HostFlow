# Принципы архитектуры HostFlow: модульная multi-company SaaS-платформа

**Позиционирование:** HostFlow — **modular multi-company SaaS platform** и **workforce operating ecosystem** для транспортной отрасли Европы: инфраструктура полного жизненного цикла транспортного персонала, документов, рекрутинга, HR, fleet operations, операционной коммуникации и **trusted workforce identity**, а также **система управления ростом** (Growth → Intake → Operations → Intelligence — [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)), а не «ещё одна большая CRM». **Цель продукта** — **trusted workforce ecosystem**: работодатели, рекрутеры, HR, fleet managers и водители в одной операционной инфраструктуре с прозрачными процессами, проверяемыми данными и непрерывной профессиональной историей. Типичные боли рынка, на которые опирается продукт: дефицит кадров, хаос в документах, отсутствие единой истории водителя, операционный шум, слабая прозрачность работодателей, медленный onboarding, недостаток доверия между сторонами, разрозненная коммуникация, отсутствие сквозного lifecycle workforce management. **Стратегическая цель** — сделать HostFlow основной **профессиональной цифровой инфраструктурой** отрасли (workforce OS, compliance layer, operational data network). **Инженерная форма:** **modular monolith** со **strict bounded contexts** и жёсткими границами модулей.

**Единая каноническая карта домена (v1):** [`hostflow-core-domain-map-v1.md`](hostflow-core-domain-map-v1.md) — цепочка Platform Core → Tenant → Company → тип → доступ к модулям → роли → scope → cross-company; таблицы GLOBAL / TENANT / COMPANY / MODULE; ownership matrix; bounded contexts и потоки событий.

Документ фиксирует **главную архитектурную логику** продукта: HostFlow — **modular multi-company SaaS platform**, а не одна монолитная CRM. Детали по подсистемам — в ADR и scope-файлах; здесь — **согласованная картина** и **формула** для принятия решений.

**Связанные нормативные документы:** [`hostflow-core-domain-map-v1.md`](hostflow-core-domain-map-v1.md), [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md), [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md), [`ADR-005`](ADR-005-three-level-settings-hierarchy.md), [`ADR-006`](ADR-006-marketplace-and-integration-platform.md), [`ADR-007`](ADR-007-forms-platform-capability.md), [`ADR-008`](ADR-008-job-publishing-and-distribution.md), [`ADR-009`](ADR-009-document-hub-platform-layer.md), [`ADR-010`](ADR-010-unified-resource-list-shell.md), [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md), [`ADR-012`](ADR-012-activity-notification-operating-layer.md), [`ADR-023`](ADR-023-recruitment-sales-module-separation.md), [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md), [`ADR-025`](ADR-025-standard-adapter-boundary.md), [`ADR-026`](ADR-026-capability-ownership.md), [`ADR-027`](ADR-027-capability-composition.md), [`platform-capability-catalog.md`](platform-capability-catalog.md), [`architecture-review-checklist.md`](architecture-review-checklist.md), [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md), [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md), [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md).

---

## 0. Platform Rules (P-01 · P-02 · P-03)

HostFlow — **платформа capabilities**, а не только набор бизнес-модулей. Фундаментальные возможности принадлежат **владельцам** и переиспользуются бизнес-модулями через композицию.

| Правило | ADR | Вопрос | Ответ |
|---------|-----|--------|--------|
| **P-01** Standard Adapter Boundary | [`ADR-025`](ADR-025-standard-adapter-boundary.md) | Как взаимодействовать? | Только **канонический** Standard Adapter |
| **P-02** Capability Ownership | [`ADR-026`](ADR-026-capability-ownership.md) | К кому обращаться? | Только к **единственному владельцу** (SoT) |
| **P-03** Capability Composition | [`ADR-027`](ADR-027-capability-composition.md) | Как строить новое? | **Композицией** существующих capabilities |

**Поток:** `Endpoint → Submission → Routing → Decision → Business Entity`  
**Граница:** `Module A → Standard Adapter → Module B`

**Catalog (boundaries):** [`platform-capability-catalog.md`](platform-capability-catalog.md)  
**Owners index:** [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) §0.1  
**PR checklist:** [`architecture-review-checklist.md`](architecture-review-checklist.md)  
**Guide:** [`architecture-guide.md`](architecture-guide.md)

Адаптер может быть локальным интерфейсом в modular monolith. Каждый модуль/capability фиксирует passport (Purpose, Owned, Public/Required contracts, Events, Settings, Data Ownership, Forbidden) — [`platform-capability-catalog.md`](platform-capability-catalog.md).

---

## 1. Базовые сущности

| Концепт | Роль |
|---------|------|
| **Tenant** | **Workspace**, граница **subscription** и **billing**; не владелец рабочих операционных данных. |
| **Company** | **Владелец данных, процессов**, включённых модулей и политик для своего контура; главная **operational / data boundary**. |
| **Module** | **Независимый продуктовый блок** (лицензируется отдельно или в bundle). |
| **Shared Platform Layer** | Общие возможности, которыми пользуются модули (Forms, Acquisition/Campaigns, Document Hub, Process Engine, …). |
| **User** | Доступ через **role + company scope + module scope**; не через «уникальные роли под каждого клиента». |

**Cross-company доступ** возможен **только** явно: **handoff**, **shared access**, **relationship** между компаниями — никакой неявной видимости «всех данных tenant».

---

## 2. Tenant: что хранит и что не хранит

Tenant **не** является владельцем рабочих сущностей (лиды, кандидаты, счета и т.д.).

**Tenant хранит / определяет:**

- Subscription, биллинг, владелец оплаты  
- Пользователи workspace (membership), **глобальная** безопасность  
- Список **доступных на аккаунте** модулей (верхняя крышка)  
- Marketplace apps / установки интеграций на уровне workspace (см. ADR-006)  
- Глобальные настройки workspace (бренд по умолчанию, locale, audit на уровне tenant — по продукту)

**Все рабочие сущности** должны принадлежать конкретной **Company** через **`owner_company_id`** (итеративное выравнивание кода — см. ADR-003), в том числе:

- leads, candidates, vacancies, clients  
- employees, vehicles  
- services, orders  
- billing_events, invoices  
- HR cases, fleet assignments  
- documents (в модели Document Hub)

---

## 3. Company и company_type

- У одной company — **один** `company_type`.  
- **Company type** — не сложная бизнес-роль с множеством вариантов; если клиенту нужны разные роли, он добавляет **дополнительные companies**.

**Примеры типов:** `agency`, `employer`, `carrier`, `service_provider` (расширяется продуктом).

**Назначение company_type:**

- onboarding presets  
- default workflows  
- suggested modules  
- dashboards  
- начальные настройки  

**Company type** — **не** жёсткая архитектурная логика модулей; это **подсказка продукта**, а не альтернатива `enabled_modules`.

---

## 4. Модели доступа к модулям

**Правильная модель:**

1. **Tenant** определяет, **какие модули доступны** в аккаунте (лицензия / крышка).  
2. **Company** определяет, **какие модули реально используются** (`enabled_modules` ∩ tenant).  
3. **User role assignment** определяет, что пользователь может делать **внутри конкретной company** и **конкретного модуля** (scope).

Клиент может купить **любую комбинацию** из пяти модулей: только Recruitment, только HR, только Fleet, только Services, только Finance — или смесь.

---

## 5. Пять независимых бизнес-модулей (ADR-004)

### 5.1 Recruitment

**Отвечает за:** leads, candidates, vacancies, **job posts**, **job publishing**, applications, подбор, **handoff кандидатов** ([`ADR-008`](ADR-008-job-publishing-and-distribution.md)).

**Не управляет:** employees, HR cases, contracts (как HR-контур), fleet, services, invoices.

**Pipeline Recruitment** — только **Lead / Candidate**; завершается статусами вроде **Hired**, **Ready for HR**, **Rejected** ([`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md)).

**Candidate** и **Employee** — **разные сущности**: candidate в Recruitment; employee в HR.

### 5.2 HR / Kadry

**Отвечает за:** Employee Profile, HR cases, employee lifecycle, contracts, ZUS, work permits, employee documents, payroll data, HR checklist, onboarding, termination.

После **Hired / Ready for HR** система **может** создать Employee и HR Case. **HR автономен:** employee может быть создан **вручную**, **импортом**, **API** без включённого Recruitment.

### 5.3 Fleet Management

- **Не** воронка: Fleet — **модуль назначений и операций**, не pipeline в CRM-смысле.  
- **Сущности:** vehicles, drivers/employees, assignments, handover, vehicle documents, damages, inspections, trip readiness, return protocols.  
- **Автономия:** Fleet может работать при выключенных Recruitment и HR; водители — из распределения, ручного ввода, import/API.

Опорная сущность: **Driver–Vehicle Assignment** / **Vehicle Assignment** (канон именования — в доменной модели).

### 5.4 Services / Orders

Отдельный модуль, **не** часть Recruitment.

**Отвечает за:** service catalog, orders, order items, delivery status, client service requests, pricing rules, **создание Billing Events**.

**Не** выставляет счета напрямую — только основание для Finance.

### 5.5 Finance / Billing

Отдельный модуль.

**Отвечает за:** billing events, invoices, payments, VAT, payment terms, billing rules, corrections / credit notes, payment status.

**Главное правило:**  
**Modules do not create invoices directly. Modules create Billing Events. Finance creates invoices.**

Billing Events могут приходить из: Recruitment, Fleet, Services, **опционально** HR — по политике продукта.

---

## 6. Shared platform capabilities

Общий слой; **не** пять ключей `enabled_modules` ADR-004 (лицензирование features — отдельно).  
Каждая строка — **platform capability** с единственным владельцем (**P-02**, [`ADR-026`](ADR-026-capability-ownership.md)); потребители ходят только через канонические адаптеры (**P-01**, [`ADR-025`](ADR-025-standard-adapter-boundary.md)).

| # | Capability | Назначение |
|---|------------|------------|
| 1 | **Forms / Public Forms** | Input layer ([`ADR-007`](ADR-007-forms-platform-capability.md)); consumers via **Endpoint Adapter** ([`ADR-025`](ADR-025-standard-adapter-boundary.md) / [`ADR-024`](ADR-024-acquisition-campaigns-intake-routing.md)). Basic core / Advanced addon. |
| 2 | **Document Hub** | Единый слой документов ([`ADR-009`](ADR-009-document-hub-platform-layer.md)). |
| 3 | **Process Engine** | Единый движок процессов: system stages, profiles, pipelines, transition/handoff rules, runtime evaluator ([`process-engine.md`](../platform/process-engine.md)). |
| 3a | **Field Registry & Card Configuration** | Канон полей, layouts, requirements ([`field-registry-card-configuration.md`](../platform/field-registry-card-configuration.md)). |
| 3b | **Entity Profile Definition Registry** | Композиция canonical fields в типы бизнес-объектов; слой между Field Registry и Intake/Process ([`entity-profile-definition-registry.md`](../platform/entity-profile-definition-registry.md)). |
| 4 | **Integrations / Marketplace** | Core integrations + apps ([`ADR-006`](ADR-006-marketplace-and-integration-platform.md)). |
| 5 | **Users / Roles / Permissions** | RBAC, матрица, scope по company и модулю. |
| 5 | **Companies** | Операционная граница, party, ACL. |
| 6 | **Settings** | Три уровня: Tenant → Company → Company Module Settings ([`ADR-005`](ADR-005-three-level-settings-hierarchy.md)). |
| 7 | **Automations** | Правила, триггеры, сценарии между сущностями. |
| 8 | **Activity & Notification Operating Layer** | Единый слой операционных действий и сигналов: задачи, напоминания, follow-up, planner, calendar, in-app bell и Notification Center. **Две сущности БД** (`Activity` + `Notification`), всё остальное — представления. **Не** два отдельных модуля «Notifications» и «Activity / Tasks»; см. [`ADR-012`](ADR-012-activity-notification-operating-layer.md) и canon [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md). |
| 9 | **Trust & Reputation Layer** | Проверенная операционная история и сигналы доверия (не «публичные blacklist» и не сырые эмоциональные отзывы); см. §6.1. |
| 10 | **Resource List Shell (SPA)** | Единая оболочка всех рабочих списков: таблица, поиск, фильтры, сортировка, колонки, rail/modal ([`ADR-010`](ADR-010-unified-resource-list-shell.md)). |
| 11 | **UI Platform Standard** | Единые токены и компоненты для всего SPA: сетка, типографика, кнопки, формы, таблицы, модалки, даты, i18n ([`ADR-011`](ADR-011-hostflow-ui-platform-standard.md)); **ревью:** чеклист и политика против дрейфа — ADR-011 §12; визуальное направление — [`pipedesign.md`](../../pipedesign.md). |

**Forms** создают/обновляют через handlers: Lead, Candidate, Employee, Client, Service Order, Fleet report, Document, Billing Profile и др. (см. ADR-007). Forms **не создают семантику полей** — только presentation/intake subset над Entity Profile ([`entity-profile-definition-registry.md`](../platform/entity-profile-definition-registry.md)).

**Document Hub** — детальная модель Document / Link / Requirement / Review — ADR-009; модули **запрашивают** required sets из Hub, не дублируют канонические списки.

**Process Engine** — system stages, process profiles, transition/handoff rules, runtime evaluator — [`process-engine.md`](../platform/process-engine.md); модули **регистрируют** свои stages и rules, не строят отдельные pipeline engines.

### 6.1 Trust & Reputation Layer, Driver App, порталы

**Trust & Reputation Layer** — это **не** публичная система «плохих работников» и **не** blacklist. Платформа строит **verified operational trust infrastructure** на **проверенных операционных событиях** (lifecycle, compliance, инциденты, назначения, стабильность, структурированные employer signals), а не на субъективных мнениях. Запросы обратной связи — **lifecycle-based**; публикация **raw emotional reviews** не является целью; допустимы **weighted operational reputation** и **verified workplace signals** при политиках приватности и согласии.

**Driver App** — критический канал экосистемы: **digital operational identity** водителя (документы, напоминания, коммуникация с рекрутером/HR/fleet, onboarding, инциденты, шаринг, **portable verified workforce identity**). Водитель управляет тем, **кому** виден профиль и какие документы доступны.

**Employer / client-facing portals** — публикация вакансий, recruitment, HR, fleet, compliance, **verified workforce data** и взаимодействие с водителями **внутри платформы**; любая **cross-company** видимость остаётся **явной** (handoff, shared access, relationship — §11).

---

## 7. Job Publishing

Внутри **Recruitment** как capability или addon ([`ADR-008`](ADR-008-job-publishing-and-distribution.md)): **Vacancy** (внутренний спрос) ≠ **Job Post** (публичная версия); flow **Vacancy → Job Post → Channel → Application Form → Lead/Candidate**.

---

## 8. Marketplace и монетизация слоёв

Integration Hub развивается в **HostFlow Marketplace** ([`ADR-006`](ADR-006-marketplace-and-integration-platform.md)):

- **Core integrations** (WhatsApp, Telegram, Email, Gmail, календари, Teams, Outlook, Drive, OneDrive, …) — **не монетизировать агрессивно** (adoption, retention).  
- **Платные:** business modules, advanced apps, advanced automations, premium marketplace apps (TMS, ERP, payroll, OCR, AI, compliance, SMS/VoIP, …).

---

## 9. Три уровня настроек (ADR-005)

1. **Tenant Settings** — subscription, billing owner, security, audit, глобальные модули, брендинг workspace, язык, timezone.  
2. **Company Settings** — company type, юрданные, пользователи company, `enabled_modules`, часы работы, подразделения, ответственные, visibility.  
3. **Company Module Settings** — пайплайны, шаблоны, чек-листы, document templates, assignment rules, billing rules, workflows, dashboards (per `module_key`).

---

## 10. Роли и scope

Принцип: **User → Role → Module → Company Scope**.

- **Нельзя** вводить роли вроде «HR Focus» / «HR Poltrakt» как отдельные системные роли.  
- **Нужна** одна роль (например **HR Officer** / **HR Employee** в продуктовой терминологии) с **разным scope** по company.

**Tenant Administrator** видит всё внутри tenant в рамках политики.  
**Platform SuperAdmin** — вне tenant, полный операторский доступ (см. код и политику безопасности).

---

## 11. Cross-company: handoff, shared access, relationships

**Cross-company visibility** только **явная**.

Передача кандидата клиенту **не** означает доступ ко всем данным agency.

**Candidate Handoff / Shared Access** (целевая модель) задаёт минимум:

- `candidate_id`, `from_company_id`, `to_company_id`  
- `shared_fields`, `shared_documents`  
- `status`, `expires_at`, `access_type`  

**CompanyRelationship** для устойчивых связей: agency–client, staffing agreement, carrier agreement, service-provider–client.

Документы при handoff — политики Document Hub (какие документы, поля, срок, download vs view, запрос исправления) — [`ADR-009`](ADR-009-document-hub-platform-layer.md).

---

## 12. Архитектурная формула (шпаргалка)

| Формула | Смысл |
|---------|--------|
| **Tenant** | Кто платит и где живёт workspace. |
| **Company** | Кто владеет данными и процессами. |
| **Module** | Какой продукт включён. |
| **User Role** | Что человек может делать. |
| **Scope** | Где именно (company + модуль). |
| **Document Hub** | Где живут документы как платформенные объекты. |
| **Forms** | Как данные входят в систему. |
| **Handoff** | Как данные переходят между company. |
| **Billing Event** | Как модули передают основание для счёта в Finance. |
| **Marketplace** | Как платформа расширяется. |

---

## 13. Карты процессов

Для построения BPM / схем начинать с **общих блоков**:

**Platform Core → Companies → Module Access → Recruitment → HR → Fleet → Services → Finance → Forms → Document Hub → Integrations/Marketplace → Handoff/Shared Access → Billing Events → Trust & operational signals (политика продукта).**

Далее строить **отдельные карты по модулю**, а не одну огромную схему всего продукта.

---

## История

- 2026-05: первичная консолидация принципов modular multi-company SaaS, границ Tenant/Company/Module, shared capabilities, RBAC, cross-company, Billing Events, ссылки на ADR-002–009.
- 2026-05: позиционирование workforce OS / trusted ecosystem; shared capability **Trust & Reputation Layer**; Driver App и employer portals; уточнение modular monolith + bounded contexts.
- 2026-05: [`ADR-010`](ADR-010-unified-resource-list-shell.md) — единая оболочка списков (SPA), field kinds, rail/modal; capability #10 в §6 (после консолидации Activity/Notification — было #11).
- 2026-05: [`ADR-011`](ADR-011-hostflow-ui-platform-standard.md) — платформенный UI-стандарт (всё стандартизируемое в приложении); capability #11 в §6; §12 — политика ревью против дрейфа.
- 2026-05: [`ADR-012`](ADR-012-activity-notification-operating-layer.md) — Activity & Notification Operating Layer (единая capability вместо двух старых строк «Notifications» + «Activity / Tasks»); canon [`activity-notification-operating-layer.md`](activity-notification-operating-layer.md). Уточнение: «Reminder», «Todo», «Planner», «Today», «Calendar» — **представления** Activity, не отдельные модули.
- 2026-07-18: [`ADR-025`](ADR-025-standard-adapter-boundary.md) — **Platform Rule P-01 Standard Adapter Boundary** (Standard Adapters Only); §0 в этом документе.  
- 2026-07-18: P-01 strengthened — canonical contracts (not ad-hoc wrappers); blockers; module contract template; governs all future ADRs.  
- 2026-07-18: [`ADR-026`](ADR-026-capability-ownership.md) — **Platform Rule P-02 Capability Ownership**; HostFlow as platform of capabilities; §0 = P-01 + P-02.  
- 2026-07-18: [`ADR-027`](ADR-027-capability-composition.md) — **P-03 Capability Composition**; checklist + capability catalog §0.1; platform canon milestone.
- 2026-07-18: [`platform-capability-catalog.md`](platform-capability-catalog.md) — **Capability Boundary** + Module/Capability Passport; P-02 operationalized.
