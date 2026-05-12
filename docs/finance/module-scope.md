# Модуль Finance / Billing: цель и границы

Продуктовый модуль **Finance / Billing** в терминах [`ADR-004`](../specs/architecture/ADR-004-five-product-modules-and-billing-events.md): агрегация **Billing Events**, счета, оплаты, корректировки, налоговая база по правилам тенанта.

## Суть

- **Входит (целевое):** приём и хранение **Billing Events** из Recruitment, Services, Fleet (и опционально HR по политике), правила агрегации, **invoices**, платежи, credit notes, статусы оплаты, отчётность для бухгалтерии.
- **Не входит:** операционное выполнение услуги, найм, управление ТС — только **учёт и выставление документов** на основании событий.

## Текущее состояние кода (наблюдение)

- Флаг тенанта **`finance`** и UI/матрица; существующие **`/api/v1/invoices`** и настройки биллинга — **до** полного слоя Billing Events. Миграция к модели «только из событий» — отдельная серия задач (ADR-004).

## Лицензирование

- Ключ: `finance`; пересечение с `Company.enabled_modules` (после enforcement).

## Сопровождение

- Сбор платёжных/юридических данных с публичной ссылки — платформенный **Forms** + handler в Finance/Client, см. [`ADR-007`](../specs/architecture/ADR-007-forms-platform-capability.md), [`../forms/module-scope.md`](../forms/module-scope.md). Вложения к счетам, договоры, подтверждения оплат — **Document Hub** ([`ADR-009`](../specs/architecture/ADR-009-document-hub-platform-layer.md), [`../document-hub/module-scope.md`](../document-hub/module-scope.md)).
- Нумерация счетов, НДС, условия оплаты, billing rules — **Company Module Settings** (`module_key=finance`): [`ADR-005`](../specs/architecture/ADR-005-three-level-settings-hierarchy.md). Схема JSON: **`FinanceModuleSettingsV1`** (`backend/app/schemas/company_module_settings_json.py`); API `GET/PATCH .../module-settings/finance`.
- При введении Billing Event pipeline обновлять этот документ, **ADR-004** и каталог маршрутов.
