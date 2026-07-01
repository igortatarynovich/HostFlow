# ADR-003: Tenant vs Company — subscription, modules, data ownership

Единый продуктовый обзор: **[`platform-architecture-principles.md`](platform-architecture-principles.md)** (Tenant = workspace/billing; Company = владелец рабочих данных; cross-company только явно).

## Status

Accepted (architecture). **Имплементация поэтапная**; часть уровня tenant уже есть (`tenant.settings.modules.*`), уровень company и scoped role assignments — в бэклоге.

## Context

Один **tenant** (workspace / billing boundary) может объединять несколько **companies** с разными ролями в бизнесе: агентство, перевозчик, операционная компания и т.д. Продукт продаёт **пять независимых модулей** (отдельно, addons, bundle) — см. [`ADR-004-five-product-modules-and-billing-events.md`](ADR-004-five-product-modules-and-billing-events.md): **Recruitment**, **HR / Kadry**, **Fleet Management**, **Services / Orders**, **Finance / Billing**. При этом:

- Включённый модуль на tenant **не должен** автоматически означать одинаковый доступ для всех companies.
- Операционная и данная граница по умолчанию — **Company**, а не «весь tenant сразу».
- Модули **слабо связаны**: Fleet-only, HR-only и Recruitment-only сценарии должны оставаться валидными без обязательных зависимостей.
- **Company type** не задаёт ownership и не заменяет ACL; он нужен для onboarding presets, дефолтных воронок/дашбордов и **предлагаемых** модулей.

## Decision

### 1. Два уровня доступа к модулям

| Уровень | Назначение | Пример |
|--------|------------|--------|
| **Tenant** | Subscription / plan / addons: какие продуктовые возможности **вообще** разрешены в аккаунте | `enabled_modules`: recruitment, hr, fleet, services, finance |
| **Company** | Какие из tenant-доступных модулей **реально включены** для данной company и её данных | Company A: recruitment only; Company B: hr + fleet; Company C: fleet + services; Company D: finance + services |

**Правило совместимости:** для company модуль может быть включён только если он включён на tenant (tenant = верхняя крышка).

### 2. Границы ответственности

- **Tenant:** биллинг, подписка, глобальные настройки workspace, платформенные лимиты, SSO и т.д.
- **Company:** владелец операционных данных и процессов в рамках разрешённых модулей; **scope** для прав пользователей и для фильтрации списков/отчётов по умолчанию.
- **Module:** продуктовая способность (свои сущности, workflows, настройки, дашборды, permissions namespace).
- **User role assignment:** что пользователь может делать **внутри пары (company, module)** и при необходимости внутри org unit / «own / assigned» (существующие паттерны supervisor/recruiter ACL развиваются в эту модель).

### 3. Владение данными: `owner_company_id`

Каноническая цель: основные сущности имеют явного владельца данных — **`owner_company_id`** (UUID company в рамках tenant). Семантика:

- Фильтры по умолчанию, отчёты, квоты и разграничение «видимости» строятся от **owner**, а не от «любой строки с тем же `tenant_id`».
- Связи **клиент ↔ агентство**, handoff, shared vacancy access остаются **контролируемым исключением** (cross-company visibility по политике, а не по умолчанию).

**Текущее состояние кода (наблюдение):** уже есть `company_id`, `own_company_id`, `operating_company_id` на разных таблицах. Миграция к единому имени и семантике — отдельная инженерная фаза; ADR фиксирует **целевую** модель, не требуя big-bang переименования в одном PR.

Целевой охват `owner_company_id` (итеративно): leads, candidates, employees (workforce), vacancies, clients, vehicles / fleet resources, assignments, HR cases / contracts / payroll сателлиты, **services / orders**, **billing_events**, **invoices**, handoffs, прочие операционные сущности модулей.

### 4. Пользователи и роли

Целевая форма назначения (концепт):

- Пользователь в tenant может иметь **несколько** назначений: `(company_id, module, role_key, optional org scope)`.
- Примеры из запроса: HR Employee для Company A; тот же человек не получает HR на Company B без отдельного назначения; Fleet Manager только на Company C.

Текущий код в основном опирается на **одну роль на membership** и **company_access** / ACL по компаниям — это **предшественник**; ADR задаёт направление эволюции без отмены существующих деплойментов в один день.

### 5. Интеграция модулей (loose coupling)

- Recruitment: Lead → Candidate → … → handoff к HR; **не** хранит услуги/счета как свой контур — только **Billing Event** при необходимости (см. ADR-004).
- HR: Employee (в т.ч. из candidate reference или вручную / API).
- Fleet: assignments / операции (в т.ч. reference на employee или вручную / API); без CRM-pipeline как у кандидата.
- Services: заказы и исполнение; **Billing Event** → Finance.
- Finance: invoices **только** из Billing Events / правил агрегации.

Запрещено проектировать «жёсткий» граф зависимостей (например «Fleet всегда требует HR»). Запрещено создавать **invoice** из Recruitment/Services/Fleet напрямую. Разрешены ссылки, события, handoffs, optional FK.

### 6. Company type

Использовать **только** для: onboarding presets, default workflows, default dashboards, suggested modules / templates. **Не** использовать как источник ownership или глобального ACL.

## Consequences

1. **Tenant-only флаги** (`tenant.settings.modules.*`) остаются **необходимыми**, но **недостаточными**: дальше — выравнивание с **пятью продуктовыми модулями** (ADR-004), **company-level `enabled_modules`**, проверки в API/listing.
2. Любой новый функционал модулей следует проектировать с вопросом: «какая **company** — owner и как проверяется module+company для пользователя?»
3. Потребуются миграции схемы и рефакторинг ACL/листингов; совместимость с существующими tenant-level gates сохраняется как **фаза 0**.
4. Документация продуктовых модулей должна ссылаться на **ADR-003** (tenant/company/data), **ADR-004** (пять модулей и Billing Events) и **ADR-005** (иерархия настроек: Tenant → Company → Company Module Settings).

## Implementation phases (рекомендуемый порядок)

1. **P0 (есть):** tenant subscription modules; гейты API уровня tenant (`fleet_access`, `hr_workforce_access`); в матрице сосуществуют **legacy-ключи** (triad, `documents`, …) и продуктовые **`recruitment`** (derived), **`finance`**. Сводная карта: [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md).
2. **P1 (частично):** tenant-ключи `recruitment` (синхрон с triad candidates+leads+vacancies) и `finance` в `tenant.settings.modules`; колонка **`companies.enabled_modules`** (JSON, nullable) + `services/company_module_access.py` (`get_effective_company_modules`). Enforcement по **company** в API — **начат** для Recruitment: candidate create/get/patch, list/count/insights/no-next-action, bulk-stage/manager, delete; vacancy get/create/patch/delete/attach (`company_module_enforcement.py`); далее — фильтр списка вакансий, **leads**, остальные модули.
3. **P2:** нормализация ownership → `owner_company_id`; **Billing Event** слой; запрет прямого создания invoice из операционных модулей.
4. **P3:** role assignments `(user, company, module, role)` + миграция с текущих `user.role` + `company_access`.

## References

- [`platform-architecture-principles.md`](platform-architecture-principles.md) — модульная multi-company платформа, `owner_company_id`, company_type, RBAC scope, handoff.  
- **ADR-005:** три уровня настроек (Tenant / Company / Module per company), рекомендуемая модель `company_module_settings`.
- **ADR-006:** Marketplace / Integration Platform — `installed_integrations` / `installed_marketplace_apps` (tenant), `enabled_integrations` (company) поверх границ ADR-003.  
- **ADR-007:** Forms / Public Forms — платформенный сбор данных; публикация и submission могут быть привязаны к company/module/сущности (см. [`ADR-007`](ADR-007-forms-platform-capability.md)).  
- **ADR-008:** Job Publishing — внутри Recruitment; vacancy/job post/channel привязаны к company и модулю recruitment.  
- **ADR-009:** Document Hub — документы с `owner_company_id`, links на сущности; handoff и shared access между компаниями.
- **ADR-004:** пять продуктовых модулей, Billing Events vs invoices, anti-scope по модулям.
- ADR-002: граница Recruitment ↔ HR на стадиях кандидата.
- `docs/specs/architecture/rbac_matrix.md` — матрица ролей (будет расширена company+module scope).
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) — ключи, маршруты, чек-лист фаз.
- `docs/hr/module-scope.md`, `docs/fleet/module-scope.md`, `docs/recruitment/module-scope.md`, `docs/services/module-scope.md`, `docs/finance/module-scope.md` — охват пяти продуктов.
- Модель `Company` (`backend/app/models/company.py`) — расширение под `enabled_modules` / `extra` в P1.
