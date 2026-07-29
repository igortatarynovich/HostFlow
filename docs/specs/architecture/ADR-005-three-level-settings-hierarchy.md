# ADR-005: Три уровня настроек — Tenant, Company, Module (per company)

## Status

Accepted (architecture). **Имплементация поэтапная.** Текущий код частично хранит всё в `tenant.settings` и в сущностях без явного слоя **Company Module Settings** — новая разработка и миграции должны следовать этому ADR.

## Context

HostFlow — multi-company workspace внутри tenant. Настройки смешивались на уровне тенанта (модули, брендинг, процессы), что мешает сценариям «один tenant — несколько компаний с разными модулями и разными пайплайнами». Нужна **иерархия из трёх уровней**, согласованная с [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md) (tenant vs company) и [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) (пять модулей).

## Decision: три уровня

### 1. Tenant Settings (глобально по workspace)

**Назначение:** что **куплено и разрешено** на аккаунте, кто администрирует workspace, общие политики — **без** операционных процессов конкретной компании.

**Входит (не исчерпывающе):**

- subscription / plan, лимиты, биллинг-владелец  
- **глобально включённые модули** (верхняя крышка лицензии)  
- пользователи тенанта (membership), глобальная безопасность, audit  
- глобальный брендинг workspace (если не переопределён company)  
- язык / часовой пояс по умолчанию для workspace  
- **presets прав по умолчанию** (шаблоны ролей / матрицы как стартовые точки, не операционный слой компании)

**Не входит:** кандидатские воронки, шаблоны Fleet, прайсинг услуг, нумерация счетов конкретной юрлица и т.п. — это **Company** или **Company Module Settings**.

### 2. Company Settings (операционный слой компании)

**Назначение:** **кто работает** и **в каком контексте** ведётся операция для данной `company` внутри tenant.

**Входит (не исчерпывающе):**

- company type (только presets / подсказки продукту — см. ADR-003 §6)  
- юридические / реквизиты, контакты  
- пользователи и роли **в привязке к company** (целевая модель; эволюция от текущего ACL)  
- **`enabled_modules` для этой company** (подмножество разрешённых tenant)  
- ответственные по умолчанию, рабочие часы  
- подразделения / команды (оргструктура как справочник company)  
- брендинг company (если нужен)  
- **правила видимости клиента** (client visibility) для этой company  

Company Settings — **основной operational configuration layer** для данных и доступов.

### 3. Module Settings (внутри конкретной company)

**Назначение:** **как именно работает модуль** у данной company: пайплайны, шаблоны, правила назначения, статусы — всё, что относится к продуктовому модулю ADR-004, но **не** к глобальному tenant и не к «сырым» реквизитам company.

Примеры по модулям (иллюстративно):

| Модуль | Примеры содержимого Company Module Settings |
|--------|---------------------------------------------|
| **Recruitment** | candidate pipelines, lead sources, vacancy templates, candidate document templates, handoff rules, recruiter assignment rules |
| **HR** | employee pipelines, employment templates, HR document templates, contract templates, ZUS checklist, work permit rules, HR assignment rules |
| **Fleet** | vehicle types, vehicle document templates, handover checklist templates, assignment rules, damage report settings, inspection templates |
| **Services** | service catalog, order statuses, service templates, delivery workflows, pricing rules |
| **Finance** | invoice numbering, VAT rates, payment terms, billing rules, payment statuses, correction rules |

### Архитектурное правило

- **Tenant** включает модули (лицензия / крышка).  
- **Company** **использует** подмножество разрешённых модулей.  
- **Module Settings** **конфигурируют поведение** каждого включённого модуля **внутри этой company**.

**Пресеты на tenant:** допустимы **только** как значения по умолчанию при создании company / включении модуля (копирование в `company_module_settings` или первичный seed), **не** как единственное хранилище операционных процессов.

**Независимость модулей:** настройки и код **не должны предполагать**, что Recruitment включён. Fleet-only, Finance-only, HR-only конфигурации должны быть полными. См. ADR-004 (слабая связность).

## Decision: рекомендуемая модель данных

Таблица (или эквивалент), нормализующая настройки модуля по company:

| Поле | Назначение |
|------|------------|
| `tenant_id` | RLS, принадлежность workspace |
| `company_id` | Компания-владелец конфигурации |
| `module_key` | Канонический ключ: `recruitment` \| `hr` \| `fleet` \| `services` \| `finance` (и при необходимости узкие подключи с префиксом по соглашению) |
| `settings_json` | JSON: структура по модулю (версионируемая схема по `module_key`) |
| `is_enabled` | Явное «модуль включён для company и сконфигурирован» (дублирует/уточняет пересечение с `company.enabled_modules` — уточнить в имплементации: одно поле-источник или derived) |
| `configured_at` | Аудит готовности конфигурации |

**Имя сущности (рекомендация):** `company_module_settings` (одна строка на пару `(company_id, module_key)` или версионированные строки — отдельное решение при миграции).

**Эффект:**

- один tenant, много companies;  
- у каждой company свой набор модулей;  
- у каждого модуля свои пайплайны, шаблоны и правила **per company**.

### Примеры компаний в одном tenant

| Company | Включённые модули (пример) |
|---------|----------------------------|
| Focus Personnel | Recruitment, HR |
| Poltrakt Transport | HR, Fleet |
| Rock Cargo | Fleet, Finance |

## Consequences

1. Новые фичи «настройки модуля» проектируются с **company scope** и `module_key`, а не как произвольные ключи в `tenant.settings`, кроме **default presets**.  
2. Существующие данные (funnels, templates, tenant.settings.modules) потребуют **постепенной** привязки к `company_id` и/или переноса в `company_module_settings` / специализированные таблицы с FK на company.  
3. API: чтение/запись настроек модуля — с **обязательным контекстом company** (и проверкой `company_allows_module`).  
4. Документация модулей и [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) ссылаются на этот ADR как на канон иерархии настроек.

## References

- [`ADR-003-tenant-company-module-data-boundaries.md`](ADR-003-tenant-company-module-data-boundaries.md)  
- [`ADR-004-five-product-modules-and-billing-events.md`](ADR-004-five-product-modules-and-billing-events.md)  
- [`ADR-006-marketplace-and-integration-platform.md`](ADR-006-marketplace-and-integration-platform.md) — целевая модель **`enabled_integrations` на company** (поверх установок tenant) и витрина Marketplace; дополняет уровни Tenant/Company здесь.  
- [`ADR-007-forms-platform-capability.md`](ADR-007-forms-platform-capability.md) — Forms как input layer; пресеты/политики публикации форм per company могут дополнять настройки без смешения с `module_key` ADR-004.  
- [`ADR-009-document-hub-platform-layer.md`](ADR-009-document-hub-platform-layer.md) — Document Hub; наборы требований и политики могут увязываться с company / модулем без владения файлом модулем.  
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)  
- `docs/hr/module-scope.md` — зона HR; целевое хранение настроек HR — Company Module Settings  

## История

- 2026-05: первичная фиксация трёх уровней и рекомендуемой таблицы `company_module_settings`.
- 2026-05: добавлены миграция `202605080001_cms`, модель `CompanyModuleSettings`, API `GET/PATCH /api/v1/companies/{company_id}/module-settings/...` (проверка `company_allows_module`, ACL company для не-админов).
- 2026-05: для ключей `hr` \| `recruitment` \| `fleet` \| `services` \| `finance` — схемы `*ModuleSettingsV1` в `company_module_settings_json.py` (PATCH валидирует, GET приводит битый JSON к умолчаниям); в SPA на карточке компании — минимальный блок настроек модулей (JSON + `is_enabled`).
- 2026-07-29: **ADR-033** — operational SoT for lead lifecycle emails (RODO + ops) is Company Module Settings (`lead_lifecycle_email_v1`); Vacancy sparse override in `vacancies.settings_json`; tenant JSON = preset/cutover only. See [`ADR-033`](ADR-033-lead-lifecycle-email-company-policy.md) · [`lead-lifecycle-email-policy.md`](../workflows/lead-lifecycle-email-policy.md).
- 2026-05: связка с **ADR-006** — на company помимо `module_settings` планируется явное **`enabled_integrations`** (установка интеграции на tenant, включение и политика — на company).
