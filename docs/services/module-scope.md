# Модуль Services / Orders: цель и границы

Продуктовый модуль **Services / Orders** в терминах [`ADR-004`](../specs/architecture/ADR-004-five-product-modules-and-billing-events.md): каталог услуг, заказы, исполнение, статусы, выход в биллинг через **Billing Events** — не через прямые счета.

## Суть

- **Входит (целевое):** каталог услуг, заказ на услугу, привязка к клиенту/компании, жизненный цикл исполнения, нормализованные события для Finance.
- **Не входит:** создание и версионирование **invoices** (→ **Finance**), рекрутерская воронка как основной объект (→ **Recruitment**), кадровые кейсы (→ **HR**).

## Текущее состояние кода (наблюдение)

- Флаг тенанта **`services`** и сопутствующие сценарии (в т.ч. `additional-services`) уже используются; **единого HTTP module-gate** уровня tenant для всего контура Services, как у `fleet` / `hr`, может не быть — выравнивание по ADR-004 — в бэклоге.
- Прямые связи услуг с кандидатом/рекрутингом — **наследие**; новая разработка должна явно отделять «заказ услуги» от «этапа кандидата», сохраняя при необходимости ссылки.

## Лицензирование

- Ключ: `services` в `tenant.settings.modules`; пересечение с `Company.enabled_modules` (после enforcement).

## Сопровождение

- Заявки, intake и отправка документов с публичных ссылок — целевой контур **Forms** (input layer), см. [`ADR-007`](../specs/architecture/ADR-007-forms-platform-capability.md), [`../forms/module-scope.md`](../forms/module-scope.md). Договоры, заказы, подтверждения — **Document Hub** ([`ADR-009`](../specs/architecture/ADR-009-document-hub-platform-layer.md), [`../document-hub/module-scope.md`](../document-hub/module-scope.md)).
- Настройки каталога/статусов/воркфлоу Services — **Company Module Settings** (`module_key=services`): [`ADR-005`](../specs/architecture/ADR-005-three-level-settings-hierarchy.md). Схема JSON: **`ServicesModuleSettingsV1`**; API `GET/PATCH .../module-settings/services`.
- Обновлять при появлении таблиц заказов, Billing Events и новых API — см. [`module-catalog-and-routing-map.md`](../specs/architecture/module-catalog-and-routing-map.md).
