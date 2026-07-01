# Модуль Forms / Public Forms: охват и роль на платформе

Документ описывает **целевой** продуктовый модуль **Forms** как **платформенную capability** (input layer), а не как подсистему только Recruitment. Нормативное архитектурное решение — **[`ADR-007`](../specs/architecture/ADR-007-forms-platform-capability.md)**.

## Суть

- **Forms** — отдельный контур: шаблоны, публикация, приём **submissions**, файлы, согласия, маппинг, триггеры автоматизаций.  
- **Recruitment, HR, Fleet, Services, Finance** — **потребители** Forms; доменные сущности и бизнес-правила остаются в соответствующих модулях.  
- **Главное правило:** Forms — это **не** синоним «анкеты кандидата». Анкета кандидата — **один** из сценариев.
- **Канон данных:** Forms **не определяют смысл полей**. Формы — поверхность ввода над **Entity Profile**, основанным на **Field Registry** — см. [`entity-profile-definition-registry.md`](../specs/platform/entity-profile-definition-registry.md).

## Режимы

| Режим | Описание |
|-------|----------|
| **Standalone** | Форма создана пользователем, выдана **публичная ссылка**; обработчик submission определяет целевую сущность по конфигурации. |
| **Linked** | Форма привязана к **модулю**, **процессу** или **конкретной сущности** (вакансия, employee, vehicle, order, client…). |

## Состав (целевая архитектура)

- **Form templates** — схема полей, версии, валидация.  
- **Public links** — slug, политика доступа, срок действия (Advanced).  
- **Submissions** — сохранённые ответы, статусы, аудит.  
- **File uploads** — вложения; регистрация в **Document Hub** как **Document** + links ([`ADR-009`](../specs/architecture/ADR-009-document-hub-platform-layer.md)).  
- **Consent capture** — RODO, oświadczenia, явные согласия (по политике продукта).  
- **Field mapping** — отображение полей формы на поля сущностей / custom fields.  
- **Automation triggers** — события для правил и сценариев платформы.

## Целевые результаты submission (handlers)

Один и тот же движок Forms должен поддерживать настройку исхода данных в сторону (не исчерпывающе):

- **Lead**, **Candidate**  
- **Employee** (workforce)  
- **Client** / company / party (по канону B2B)  
- **Service Order**  
- Записи **Fleet** (damage, inspection, handover, return, trip issue, fuel/card confirmation — уточнение в доменном API)  
- **Document** (файл + метаданные)  
- **Billing profile** / реквизиты для счетов  

## Примеры по модулям-потребителям

### Recruitment

- Анкета кандидата  
- Форма отклика на вакансию (**связана с Job Post** в контуре Job Publishing — [`ADR-008`](../specs/architecture/ADR-008-job-publishing-and-distribution.md))  
- Обновление данных кандидата  
- Загрузка документов  
- Предварительная квалификация  
- RODO consent  
- Форма для клиента: оценка кандидата  

### HR

- Анкета сотрудника  
- Сбор данных для ZUS  
- PIT-2 / налоговые данные  
- Банковские реквизиты  
- Согласия и oświadczenia  
- Обновление данных сотрудника  
- Onboarding form  

### Fleet

- Vehicle handover checklist  
- Damage report  
- Vehicle return  
- Inspection  
- Driver trip issue report  
- Fuel / card / equipment confirmation  

### Services

- Service request  
- Client order  
- Intake  
- Document submission  

### Finance

- Billing details  
- Данные для счёта / обновление  
- Payment confirmation  

## Basic vs Advanced (продукт)

| Tier | Содержание |
|------|------------|
| **Basic** | Создание формы, публичная ссылка, сбор submissions, загрузка файлов — **включено в платформу** / baseline. |
| **Advanced** | Условные поля, маппинг на сущности, автоматизации, e-signature / consent tracking, интеграция с чек-листами документов, брендирование, мультиязычность, истечение ссылок, связка с порталами кандидата/клиента — **платный addon** и/или часть пакетов модулей. |

## Текущий код (наблюдение)

- **Lead forms:** `tenant_lead_forms`, квоты, UI настроек лид-форм, публичный intake — исторически ориентированы на лиды/кандидатов. Эволюция к универсальной модели Forms описана в **ADR-007** (миграция схемы и API — поэтапно).  
- См. также [`../specs/lead-types.md`](../specs/lead-types.md), [`../SSOT.md`](../SSOT.md).

## Сопровождение

- При добавлении нового **публичного** сценария сбора данных проверять: не дублировать «ещё один специальный intake», а расширять **Forms** + handler модуля.  
- Обновлять этот файл и **ADR-007** в одном изменении с продуктовыми решениями по маппингу и биллингу Advanced.

## История

- 2026-05: первичная фиксация scope Forms как платформенного модуля и матрица примеров по потребителям.
