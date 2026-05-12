# Редизайн профиля клиента и модуля вакансий

## Текущее состояние

### Что есть на странице профиля клиента (`/app/clients/:id`)

| Блок | Поля / Содержимое | Проблема |
|------|-------------------|----------|
| **Хедер** | Название, юр. название, локация, кнопки сохранения | OK |
| **KPI‑карточки** | candidates_total, candidates_pipeline, candidates_docs, vacancies_active, services_blocking | Часть неочевидна; `services_blocking` — что блокирует? |
| **Overview** | Основной контакт, финансовый контакт, ближайший контракт, открытые слоты водителей | **Транспортоцентрично** (driver slots). Для non-transport — бесполезно |
| **Вакансии (виджет)** | Суммарно, по статусам, последние 4 | Дублирует реальные вакансии; данные из `extra.company_vacancies` — могут быть не синхронизированы |
| **Blockers** | Заказы с незаполненными полями (schedule, capacity, status, documents) | **Транспортоцентрично** (required_drivers, hired_drivers) |
| **Счета (ClientInvoicesBlock)** | Счета клиента | OK — нужно для фактуры |
| **Readiness** | has_legal, contact, billing, compliance, portal | Полезно, но много бейджей |
| **Base** | name, legal_name, tax_id, phone, email, website, country_code, city, address, archived, notes | Смешаны базовые и фактурные данные |
| **Legal** | reg_no, vat_eu, established_at, transport_license, insurance, registered_address, operational_address, authorized_representatives | `transport_license`, `insurance` — транспортные; `reg_no`/`vat_eu` — дублируют tax_id в разных юрисдикциях |
| **Billing** | currency, payment_terms, invoice_email, billing_address, Peppol, bank_accounts | OK — нужны для фактуры |
| **Contacts** | role, full_name, email, phone, is_primary, is_portal_user | OK |
| **Operations** | fleet_tractors, fleet_intl_perc, fleet_local_perc, drivers_total, has_adr, work_modes, trailer_types (mega/standard/frigo/container), lanes (origins/destinations), cargo_types, languages, preferred_nationalities | **100% транспорт** — для IT, ритейла, производства не нужны |
| **Compliance** | fin_check_status, aml_required, iso9001, doc_valid_until, last_check | Часть общая (fin_check, doc_valid), часть — специфика (aml, iso) |
| **Portal** | enabled, url, last_sync, portal_roles, permissions (JSON) | Для портала — OK, но `permissions` как raw JSON — неудобно |
| **Integrations** | provider_ids, logo_url, primary_color, webhooks | provider_ids, webhooks — для интеграторов; branding — для white‑label |
| **Contracts** | title, status, starts_at, ends_at, reference | OK |
| **Orders** | title, status, dates, required_drivers, hired_drivers, client_reference | **Транспортоцентрично** (drivers). Для других отраслей — «заявки» с другими полями |
| **Document Policies** | Политики документов для клиента | OK — нужно |

### Лишнее или избыточное

1. **KPI `services_blocking`** — без контекста непонятно; лучше убрать или пояснить.
2. **Overview «driver_slots»** — только для транспорта.
3. **Blockers** — завязан на модель заказов с водителями; для других отраслей — пустой или бессмысленный.
4. **Legal: transport_license_number, insurance_policy_no** — транспортные; вынести в настраиваемый профиль или убрать из базового.
5. **Operations** — весь блок транспортоцентричен; для non-transport — скрывать или заменять на настраиваемый «операционный профиль».
6. **Orders** — поля `required_drivers`, `hired_drivers` — только транспорт; нужна настраиваемая модель «заявки».
7. **Integrations: branding (logo, color)** — для большинства не нужны; можно в «расширенные настройки».
8. **Portal: permissions (JSON)** — сложно редактировать; лучше простые флаги или preset’ы.

---

## Рекомендуемая структура профиля клиента

### Уровень 1: Всегда видно (core)

| Секция | Поля | Назначение |
|--------|------|------------|
| **Фактура и юр. данные** | legal_name, tax_id (NIP/regon/VAT), country | Минимум для счёта и договора |
| **Адреса** | registered_address (юридический), operational_address (офис) | Юр. адрес — для документов, офис — для контактов |
| **Контакты и роли** | contacts[]: role, full_name, email, phone, is_primary | Кто с кем говорит |
| **Банковские счета** | bank_accounts[]: iban, swift, bank_name, is_primary | Для оплаты |
| **Billing** | default_currency, payment_terms_days, invoice_email, billing_address | Выставление счетов |

### Уровень 2: По необходимости (collapsible)

| Секция | Поля | Когда показывать |
|--------|------|------------------|
| **Счета** | ClientInvoicesBlock | Всегда, но компактно |
| **Контракты** | title, status, dates, reference | Всегда |
| **Заказы/заявки** | **Настраиваемые** (см. ниже) | Всегда, но структура зависит от типа клиента |
| **Вакансии** | Список вакансий клиента + ссылка на Pipeline | Всегда |
| **Document policies** | Требования к документам | Всегда |

### Уровень 3: По типу клиента (настраиваемый операционный профиль)

Операционный профиль — **конфигурируемый** на уровне tenant/отрасли:

- **Транспорт**: fleet (tractors, intl/local), trailers, lanes, cargo_types, drivers_total, work_modes, has_adr, languages, nationalities.
- **Производство**: capacity, equipment, certifications, regions.
- **IT/офис**: team_size, roles, tech_stack.
- **Ритейл**: locations_count, format, categories.

Реализация: справочник «типы операционного профиля» + JSON‑схема полей. UI рендерит форму по схеме.

### Уровень 4: Служебное (advanced / скрыто по умолчанию)

| Секция | Назначение |
|--------|------------|
| Compliance | fin_check, doc_valid_until, aml, iso — показывать только если включён модуль compliance |
| Portal | Показывать только если используется клиентский портал |
| Integrations | provider_ids, webhooks — для интеграторов |
| Readiness | Оставить, но компактнее — один бейдж + expand |

---

## Заявки (Orders) — настраиваемые

Текущая модель заказов — под транспорт (required_drivers, hired_drivers). Для универсальности:

1. **Типы заявок** (настраиваются в Settings):
   - Транспорт: title, status, dates, required_drivers, hired_drivers, reference.
   - Офис/IT: title, status, dates, headcount, hired_count, position_type, reference.
   - Производство: title, status, dates, quantity, delivered, unit, reference.

2. **Общие поля для всех типов**: title, status, starts_at, ends_at, client_reference, custom_fields (JSON).

3. **Специфичные поля** — через конфиг по `order_type_id`. UI подставляет форму по типу.

---

## Вакансии — анализ и улучшения

### Текущие проблемы

1. **Стиль**: VacancyDetail/VacancyList — отдельная экосистема (другие кнопки, layout, компоненты), не совпадает с Companies/Candidates.
2. **Функциональность**:
   - Вакансии на странице клиента — виджет с `extra.company_vacancies` (часто не синхронизирован с реальными вакансиями).
   - Нет быстрого перехода «создать вакансию для клиента» из карточки клиента.
   - Pipeline и Vacancies — разная навигация и контекст.
3. **Модульность**: поля вакансии жёстко заданы (title, status, salary, employment_type, candidate_profile_id); нет конфигурируемых блоков под разные типы позиций.

### Рекомендации по вакансиям

| Цель | Решение |
|------|---------|
| Единый стиль | Использовать те же компоненты (SectionCard, FieldGrid, StatusBadge), тот же layout, что у Companies и CandidateCard |
| Связь клиент ↔ вакансии | Вакансии клиента — через API `/vacancies?company_id=X`; убрать зависимость от `extra.company_vacancies` |
| Быстрое создание | Кнопка «+ Вакансия» в карточке клиента → открывает форму с предзаполненным company_id |
| Контекст | В карточке клиента — блок «Вакансии» с таблицей (название, статус, кол-во кандидатов, ссылка) + переход в Pipeline по вакансии |
| Конфигурируемость | Candidate profiles + funnel stages уже есть; добавить опциональные блоки: «Требования», «Бенефиты», «Документы» — через настройки типа вакансии |

### Модули вакансии по целям

| Модуль | Цель | Поля |
|--------|------|------|
| **Основное** | Создать и отслеживать позицию | title, company_id, status, description, location |
| **Компенсация** | Фильтр кандидатов, офферы | salary_from, salary_to, currency, employment_type |
| **Профиль кандидата** | Воронка и этапы | candidate_profile_id, funnel_id |
| **Требования** | Матчинг | requirements (текст или structured), experience_years |
| **Документы** | Compliance | document_policies (уже есть) |
| **Таймлайн** | Планирование | deadline, start_date |
| **Кандидаты** | Pipeline | Вкладка или ссылка на Pipeline filtered by vacancy |

Вакансия должна собирать эти модули в табы/секции, как в CandidateCard: Info, Candidates, Documents, Notes. Стиль — как в Companies.

---

## План изменений (приоритеты)

### Фаза 1: Упрощение профиля клиента (без смены модели)

1. Убрать или свернуть: KPI `services_blocking`, Overview «driver_slots», Blockers (или показывать только при наличии transport orders).
2. Секции Legal, Operations, Compliance, Portal, Integrations — все collapsible, defaultOpen: false.
3. Billing, Contacts, Bank accounts — наверх; Base объединить с Legal (name, legal_name, tax_id, addresses).
4. Чётко разделить: «Фактура», «Адреса», «Контакты», «Счета», «Заказы», «Вакансии».

### Фаза 2: Настраиваемый операционный профиль

1. Tenant/Company setting: `operational_profile_type` = `transport` | `office` | `custom` | `none`.
2. При `transport` — показывать текущий Operations как есть.
3. При `office` / `custom` — форма по JSON‑схеме из настроек.
4. При `none` — скрыть Operations.

### Фаза 3: Настраиваемые заявки

1. Модель `OrderType` (id, tenant_id, name, schema_json).
2. У заказа — `order_type_id`; UI рендерит поля по schema.
3. Дефолтный тип «Транспорт» — текущие поля (required_drivers, hired_drivers).

### Фаза 4: Вакансии — единый стиль и связь с клиентом

1. Редизайн VacancyDetail: SectionCard, FieldGrid, те же кнопки и layout, что у Companies.
2. На странице клиента: блок «Вакансии» с данными из `/vacancies?company_id=...`, не из extra.
3. Кнопка «+ Вакансия» в карточке клиента.
4. Табы в VacancyDetail: Info | Candidates | Documents | Notes — как в CandidateCard.

---

## Итоговый чеклист полей профиля клиента

### Оставляем (обязательные / часто используемые)

- **Фактура**: legal_name, tax_id, country, billing_address, invoice_email, default_currency, payment_terms_days, bank_accounts.
- **Адреса**: registered_address, operational_address (офис).
- **Контакты**: role, full_name, email, phone, is_primary, is_portal_user.
- **Контракты**: title, status, starts_at, ends_at, reference.
- **Заказы**: базовая структура + настраиваемые поля по типу.
- **Вакансии**: виджет со ссылкой на список и Pipeline.
- **Document policies**: требования к документам.

### Убираем / переносим

- transport_license, insurance_policy — в настраиваемый Operations (только для transport).
- Весь Operations — в настраиваемый блок по типу клиента.
- services_blocking KPI — убрать или заменить на «активные услуги».
- driver_slots overview — только при operational_profile_type = transport.
- Blockers — только при transport и при наличии заказов.
- Integrations (provider_ids, webhooks, branding) — в «Расширенные настройки».
- Portal permissions JSON — заменить на простые опции или presets.
