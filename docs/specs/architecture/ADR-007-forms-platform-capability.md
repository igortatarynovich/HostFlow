# ADR-007: Forms / Public Forms — платформенный модуль ввода данных

## Status

**Accepted (product & architecture direction).** Имплементация **поэтапная**. Текущий код (**`tenant_lead_forms`**, публичный **`/public/intake`**, квоты lead forms) исторически завязан на сценарии лидов/кандидатов — это **не отменяет** целевую модель ниже; новая разработка выносит **Forms** в **независимый контур**, а Recruitment использует его как **один из потребителей**.

## Context

Формы не должны восприниматься как «анкета кандидата» или как часть только Recruitment. **Анкета кандидата** — **один use case** модуля **Forms**. Остальные модули (HR, Fleet, Services, Finance) и кросс-модульные сценарии нуждаются в том же **input layer**: публичные ссылки, сбор данных, файлы, согласия, маппинг в сущности.

Связанные документы:

- Пять продуктовых модулей — [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) (**Forms не является шестым продуктовым модулем ADR-004**).  
- Границы tenant/company — [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md).  
- Три уровня настроек — [`ADR-005`](ADR-005-three-level-settings-hierarchy.md) (пресеты форм per company / per module — по мере внедрения).  
- Слои платформы и монетизация baseline vs paid — [`ADR-006`](ADR-006-marketplace-and-integration-platform.md).  
- Entity Profile Definition Registry (composition layer) — [`entity-profile-definition-registry.md`](../platform/entity-profile-definition-registry.md).  
- Детали текущего public intake / lead types — [`../lead-types.md`](../lead-types.md), [`../../SSOT.md`](../../SSOT.md).

## Decision: Forms = отдельная платформенная capability

**Forms** — **input layer** для всей платформы: точка входа данных в HostFlow. Модули **Recruitment, HR, Fleet, Services, Finance** подключают Forms к своим процессам; доменная логика остаётся в модулях, а Forms отвечает за **шаблон, публикацию, приём submission, вложения, согласия, базовый маппинг и триггеры**.

### Режимы

| Режим | Описание |
|-------|----------|
| **Standalone** | Пользователь создаёт форму и получает **публичную ссылку**; назначение сущности задаётся конфигурацией формы (generic или позже уточняется правилами). |
| **Linked** | Форма **привязана** к модулю, процессу или конкретной сущности (вакансия, сотрудник, ТС, заказ, клиент и т.д.); submission несёт контекст привязки. |

### Состав модуля Forms (целевая функциональность)

- **Form templates** — схема полей, валидация, версии.  
- **Public links** — slug, срок жизни, доступ.  
- **Submissions** — принятые ответы, статус, идемпотентность, аудит.  
- **File uploads** — безопасное хранение, связь с Document где применимо.  
- **Consent capture** — RODO / oświadczenia / явные согласия (по политике продукта).  
- **Field mapping** — правила «поле формы → `qualified_code` Field Registry / Entity Profile»; форма **не создаёт** новую семантику поля.  
- **Automation triggers** — события для rules / workflows (см. существующий контур автоматизаций).

### Целевые типы результатов (submission handlers)

Форма должна уметь **создавать или обновлять** (через настроенный handler), в частности:

- **Lead**  
- **Candidate**  
- **Employee** (workforce profile)  
- **Client** / party / company record (по канону данных)  
- **Service Order**  
- **Fleet** сущности (например damage report, inspection record — уточнение в доменных сервисах)  
- **Document** (метаданные + файл) — создаётся/регистрируется в **Document Hub** ([`ADR-009`](ADR-009-document-hub-platform-layer.md)) при загрузке из формы или модуля.    
- **Billing profile** / платёжно-юридические реквизиты клиента  

**Примеры:**

- Форма отклика на вакансию → **Lead** / **Candidate** (Recruitment), обычно через привязку к **Job Post** и каналу публикации — см. [`ADR-008`](ADR-008-job-publishing-and-distribution.md).  
- Анкета сотрудника → обновление **Employee Profile** (HR).  
- Форма повреждения ТС → создание **Fleet damage report**.  
- Форма заказа услуги → **Service Order**.  
- Форма данных для счёта → обновление **client billing data** (Finance).

---

## Продуктовое разделение: Basic vs Advanced

| Tier | Входит (ориентир) | Монетизация |
|------|-------------------|-------------|
| **Basic Forms** | Создать форму, публичная ссылка, сбор submissions, загрузка файлов | **Free / core platform** (см. ADR-006: platform capabilities, adoption) |
| **Advanced Forms** | Условные поля, маппинг на сущности, автоматизации, e-signature / consent tracking, чек-листы документов, брендирование, мультиязычность, истечение ссылок, связка с candidate/client portal | **Paid addon** и/или **входит в состав** соответствующих business modules / планов |

---

## Связь с ADR-004

Каталог **пяти продуктовых модулей** не расширяется полем «Forms». Лицензирование форм — **отдельная ось** (Basic включён в платформу; Advanced — addon/bundle). При необходимости в `tenant.settings.modules` или лицензии может появиться явный флаг **`forms_advanced`** (или эквивалент) — **не** смешивать с `recruitment` / `hr` / `fleet` / `services` / `finance` как с одним типом сущности.

---

## Примеры use case по модулям-потребителям

**Recruitment:** анкета кандидата; отклик на вакансию; обновление данных кандидата; загрузка документов; предквалификация; RODO consent; форма «оценить кандидата» для клиента.

**HR:** анкета сотрудника; ZUS; PIT-2 / налоговые данные; банковские реквизиты; согласия и oświadczenia; обновление данных сотрудника; onboarding form.

**Fleet:** handover checklist; damage report; return form; inspection; driver trip issue; fuel/card/equipment confirmation.

**Services:** service request; client order; intake; document submission.

**Finance:** billing details; обновление данных для invoice; payment confirmation.

Детализация полей и статусов — в [`../../forms/module-scope.md`](../../forms/module-scope.md).

---

## Consequences

1. Новые публичные формы **вне** чистого Recruitment проектируются в терминах **Forms** + **target entity**, а не как «ещё одна lead form».  
2. Рефакторинг: **`TenantLeadForm`** / маршруты intake постепенно приводятся к общей модели **FormTemplate / FormPublish / Submission** (имена и миграции — отдельные задачи).  
3. Документация модулей (recruitment, hr, fleet, …) ссылается на этот ADR там, где речь о **публичном сборе данных**.  
4. Безопасность: публичные ссылки, rate limit, антиспам, PII — общие политики платформы.

## References

- [`ADR-002`](ADR-002-modular-recruitment-hr-boundary.md)  
- [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md)  
- [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md)  
- [`ADR-005`](ADR-005-three-level-settings-hierarchy.md)  
- [`ADR-006`](ADR-006-marketplace-and-integration-platform.md)  
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)  
- [`ADR-008-job-publishing-and-distribution.md`](ADR-008-job-publishing-and-distribution.md) — Job Post → Application Form → Candidate  
- [`ADR-009-document-hub-platform-layer.md`](ADR-009-document-hub-platform-layer.md) — вложения форм → документы платформы  
- [`../../forms/module-scope.md`](../../forms/module-scope.md)

## История

- 2026-05: первичная фиксация Forms как платформенной capability, Basic/Advanced, standalone/linked, целевые handlers и примеры по модулям.
- 2026-05: связка с **ADR-008** (форма отклика в цепочке Job Publishing).
- 2026-05: связка с **ADR-009** (документы из форм — в Document Hub).
