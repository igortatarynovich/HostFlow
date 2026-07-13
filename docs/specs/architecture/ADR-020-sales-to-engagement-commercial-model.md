# ADR-020: Sales-to-Engagement Commercial Model

**Status:** Accepted (architectural direction)  
**Date:** 2026-07-13  
**Layer of change:** Domain | Life Cycle | Constitution  
**Start / Optimize / Scale:** Start (MVP vertical slice: targeting + paid invoice)  
**Authors:** Product + Platform architecture  
**Related:** [ADR-004](ADR-004-five-product-modules-and-billing-events.md), [ADR-003](ADR-003-tenant-company-module-data-boundaries.md), [ADR-017](ADR-017-workspace-layer.md), [ADR-019](ADR-019-automation-capability-entitlement-control-plane.md), [ui-constitution-v1.md](ui-constitution-v1.md), [module-catalog-and-routing-map.md](module-catalog-and-routing-map.md)

> **Terminology (обязательно):** продуктовое **«Клиент»** в UI = **`ClientAccount`** (операционные отношения). **`Company`** = юридическое лицо / party. **`Lead`** остаётся внутренним transport-слоем intake; в Sales UI — только **«Обращение»** (Sales Inquiry).

---

## 1. Context

HostFlow продаёт услуги (таргетинг, рекрутинг, Fleet Services, консалтинг, подписки). Текущий операционный путь:

```text
Meta / Forms → Lead (client_lead) → Sales Inquiry → convert-client → Company → ServiceOrder → Invoice
```

Проблемы текущей модели:

1. **`Company` смешивает три роли:** операционный клиент, юридическое лицо, плательщик. Поля расползаются в `Company.extra`, `Lead`, `Contact`, `ServiceOrder`.
2. **Нет слоя коммерческого предложения:** стадия `proposal` в воронке — не объект; нельзя версионировать оффер.
3. **Договор и оплата смешаны с продажей и исполнением:** нет отдельного Commercial Confirmation; invoice привязан напрямую к заказу без lifecycle основания.
4. **Service Order создаётся без readiness gate:** нет разделения «заказ согласован» / «можно запускать» / «идёт исполнение».
5. **Нет shortcut paths:** менеджер вынужден проходить CRM-этапы даже для «выставьте счёт».

Цель ADR: зафиксировать канон **Sale → Order & Commerce → Activation → Delivery**, пригодный для таргетинга в MVP и для Recruitment Services, Fleet, подписок — без перестройки ядра.

---

## 2. Decision: три независимых слоя

| Слой | Вопрос | Владелец (модуль) |
|------|--------|-------------------|
| **Sale** | Клиент хочет купить? | Sales (Services intake surface) |
| **Order & Commerce** | Есть заказ и юридико-финансовое основание? | Services + Finance |
| **Activation** | Можно передавать в исполнение? | Platform Readiness + Services |
| **Delivery** | Услуга оказывается и измеряется? | Services (+ Recruitment для performance-услуг) |

**Запрещено** смешивать слои:

- Оплата, договор, e-podpis, Stripe Checkout — **Commercial Confirmation**, не этапы воронки.
- Meta access, креативы — **Readiness**, не стадии Quote.
- Кампании и KPI — **Engagement**, не поля Invoice.

Это позволяет подключать новые способы оплаты и подписания **без изменения** процесса исполнения.

---

## 3. Decision: Party model — ClientAccount отдельно от Company

### 3.1 Сущности

| Entity | Class | Назначение |
|--------|-------|------------|
| **ClientAccount** | Business | Операционные отношения с клиентом: владелец, статус, сегмент, LTV, кредитный лимит, настройки, портал, история заказов |
| **Company** | Business (party) | Юридическое лицо: NIP, адрес, реквизиты, договорные документы |
| **Contact** | Business | Физическое лицо |
| **ClientAccountPartyLink** | Support | Связь аккаунта с contacts/companies и ролями (phase 2) |

**`ClientAccount` — не UI-фасад над `Company`.** У сущности собственный стабильный `id` и lifecycle.

### 3.2 Правила

- **Client Account создаётся раньше Company**, когда известен контакт, но неизвестно юрлицо плательщика.
- **Company создаётся**, когда появляются реквизиты или известен плательщик.
- **Один Client Account** может иметь **несколько Companies** (группа, филиалы).
- **Один Service Order** всегда имеет `client_account_id`; `billing_company_id` — **nullable** до выставления счёта.
- **Invoice.company_id** — конкретный получатель фактуры (может отличаться от `primary_company_id` аккаунта).

### 3.3 ClientAccount — минимальная схема (MVP, Stage 1)

Таблица `client_accounts`:

| Поле | Назначение |
|------|------------|
| `id` | Стабильный идентификатор клиента |
| `tenant_id` | Tenant (RLS) |
| `owner_company_id` | Operating company tenant'а (ADR-003) |
| `display_name` | Продуктово отображаемое имя |
| `status` | `prospect` \| `active` \| `inactive` |
| `owner_user_id` | Ответственный менеджер |
| `primary_contact_id` | Основной контакт (nullable на ранней стадии) |
| `primary_company_id` | Основное юрлицо (nullable) |
| `source_inquiry_id` | Источник создания (nullable) |
| `created_at` / `updated_at` | Аудит |

Расширяемые поля (segment, credit_limit, portal_settings, lifetime_value) — **на ClientAccount**, не в `Company.extra`.

### 3.4 Поэтапная миграция (без тяжёлой переделки)

**Stage 1 — совместимость с текущим `convert-client`:** implementation contract — [`stage-1a-client-account-implementation-contract.md`](../tasks/stage-1a-client-account-implementation-contract.md).

1. Создаётся существующая `Company` (как сегодня).
2. **Параллельно** создаётся `ClientAccount`.
3. `ClientAccount.primary_company_id` → эта `Company`.
4. Legacy-экраны могут продолжать использовать `Company`.
5. **Новые** Quote и ServiceOrder используют `client_account_id`.

**Stage 2 — party graph:**

- Таблица `client_account_party_links` (account ↔ contact/company, role: `payer`, `signer`, `operational`, `owner`, `subsidiary`).
- `primary_company_id` остаётся shortcut, не единственной связью.

---

## 4. Decision: Sale layer — необязательные ступени

### 4.1 Допустимые пути

Все пути **валидны**; система не блокирует shortcut:

| Сценарий | Путь |
|----------|------|
| Классический B2B | Inquiry → Opportunity → Quote → SO |
| «Выставьте счёт» | Inquiry → Quote → SO |
| Fast path | Inquiry → SO |
| Повторный клиент | ClientAccount → Quote → SO |

**Opportunity** — опциональный инструмент для сложных сделок (phase 2). **Не gate.**

### 4.2 Sales Inquiry

- Продуктовое имя: **«Обращение»** (UI Constitution).
- Внутренний transport: `Lead` (`lead_type=client`, `lead_target_type=client_lead`).
- Поля: `client_account_id` nullable до идентификации клиента.
- Outcome первого контакта определяет следующий объект (Opportunity, Quote, SO, close, nurture).

### 4.3 Quote (не Proposal)

| Аспект | Канон |
|--------|-------|
| Код / модель | **`Quote`** |
| UI (RU) | «Коммерческое предложение» |
| UI (EN) | Quote / Commercial offer |

**Quote lifecycle:**

```text
draft → sent → viewed → accepted | rejected | expired | replaced
```

**Quote acceptance** = клиент согласился с предложением.  
**Это не Commercial Confirmation** (см. §6).

**Scope (MVP):** versioned structured snapshot **внутри Quote** (`scope_snapshot` JSON). При создании Service Order копируется в `service_orders.scope_snapshot`. Отдельная таблица Scope — phase 2.

Пример scope snapshot:

```json
{
  "version": 1,
  "markets": ["PL"],
  "campaigns_count": 2,
  "creatives_limit": 3,
  "target_audience": "CE drivers",
  "duration_days": 30,
  "deliverables": ["meta_setup", "campaign_launch", "weekly_report"]
}
```

---

## 5. Decision: Service Order — центральный post-sale объект

### 5.1 Связи (MVP)

| Поле | Назначение |
|------|------------|
| `client_account_id` | Кто является клиентом (обязательно) |
| `billing_company_id` | Кому выставляется счёт (nullable до invoicing) |
| `quote_id` | Источник коммерции (nullable для fast path) |
| `scope_snapshot` | Копия scope на момент создания заказа |

### 5.2 Lifecycle

```text
draft
  → pending_confirmation
  → confirmed
  → onboarding
  → ready
  → active
  → completed | cancelled
```

| Статус | Значение |
|--------|----------|
| `draft` | Черновик заказа, ещё не предложен клиенту |
| `pending_confirmation` | Заказ согласован клиентом; **SO существует**; Commercial Confirmation **не завершён** |
| `confirmed` | Commercial Confirmation method выполнил обязательные milestones |
| `onboarding` | Собираем readiness (доступы, материалы) |
| `ready` | `activation_allowed = true` |
| `active` | Исполнение начато |
| `completed` / `cancelled` | Терминальные |

**Правило:** Service Order создаётся **после согласования заказа, до оплаты**. Иначе Invoice не к чему привязать.

`confirmed` ≠ «заказ создан». `confirmed` = **Commercial Confirmation completed**.

---

## 6. Decision: Commercial Confirmation — отдельный процесс

### 6.1 Разделение событий

| Событие | Слой | Пример |
|---------|------|--------|
| Quote accepted | Sale | Клиент согласился с ценой и scope |
| Invoice issued | Commerce | Счёт выставлен |
| Payment received | Commerce | Деньги получены |
| **Commercial confirmation completed** | Commerce | Все milestones метода выполнены → SO → `confirmed` |

Для `accepted_quote` acceptance и confirmation **могут совпасть**.  
Для `paid_invoice`:

```text
quote accepted → invoice issued → payment received → confirmation completed
```

### 6.2 CommercialConfirmation — экземпляр процесса (MVP)

Таблица `commercial_confirmations`:

| Поле | Назначение |
|------|------------|
| `id` | Идентификатор |
| `tenant_id` | RLS |
| `service_order_id` | Заказ (1:1 в MVP) |
| `method_code` | Код метода из registry |
| `status` | `pending` \| `in_progress` \| `completed` \| `failed` \| `cancelled` |
| `milestones_json` | Состояние обязательных шагов |
| `completed_at` | Аудит |
| `audit_trail` | История переходов |

**Не заменять** экземпляр одним полем `commercial_basis_type` на SO. Поле на SO — **денормализованный shortcut** (`confirmation_status`, `confirmation_method_code`) для UI; source of truth — `CommercialConfirmation`.

### 6.3 Commercial Confirmation Method — extensible registry

Registry (код / конфиг, не жёсткий DB enum):

| `method_code` (MVP) | Обязательные milestones | Сигнал завершения |
|---------------------|-------------------------|-------------------|
| `paid_invoice` | `quote_accepted`, `invoice_issued`, `payment_received` | Payment linked to invoice |
| `accepted_quote` | `quote_accepted` | Quote status = accepted |
| `signed_agreement` | `quote_accepted`, `agreement_signed` | Document Hub link (phase 2) |
| `manual_postpay` | `manager_approval` | Role-gated approval (phase 2) |

Future (registry only, не MVP): `stripe_checkout`, `e_signature`, `marketplace_order`, `purchase_order`, `framework_agreement`.

Правило выбора метода: **по шаблону услуги + политике tenant + атрибутам ClientAccount** (не ручной выбор менеджером без override).

**MVP default для таргетинга:** `paid_invoice`.

---

## 7. Decision: Activation Readiness — platform primitive

### 7.1 Контракт (MVP: встроен в Service Order)

Таблица `service_order_readiness_checks` (или JSON block с нормализованным API):

Каждая проверка:

| Поле | Назначение |
|------|------------|
| `check_key` | Стабильный ключ (`commercial`, `meta_access`, `creative_assets`, …) |
| `domain` | `sales` \| `services` \| `recruitment` \| `hr` \| `fleet` |
| `status` | `pending` \| `passed` \| `failed` \| `waived` |
| `is_blocking` | Критическая проверка |
| `weight` | Вес для score (информационный) |

### 7.2 Два результата (обязательно)

| Результат | Тип | Назначение |
|-----------|-----|------------|
| `readiness_score` | 0–100 | UX-прогресс; **не** gate |
| `activation_allowed` | boolean | Строгий gate запуска |
| `blocking_checks[]` | list | Причины запрета |

**Запрещено** решать запуск по среднему проценту.  
Пример: Commercial ✅, Materials 90%, Meta access ❌ → score ≈ 80%, **`activation_allowed = false`**.

Критические (`is_blocking=true`) проверки **не компенсируются** выполненными некритическими.

### 7.3 Platform evolution (post-MVP)

Модули регистрируют **ReadinessContributor** в Workspace Readiness (module-catalog §0). Services — первый consumer; Recruitment, HR, Fleet — те же контракты.

**Onboarding Case** (универсальный Process Engine: client / employee / supplier / carrier) — **phase 2**. MVP: checklist на Service Order.

---

## 8. Decision: Delivery — Engagement условен

### 8.1 Правило

| Объект | Обязательность |
|--------|----------------|
| **ServiceOrder** | Обязателен для любой проданной услуги |
| **Engagement** | Только для услуг с `execution_mode = ongoing` в шаблоне каталога |

`execution_mode` на Service catalog item:

| Значение | Delivery path |
|----------|---------------|
| `ongoing` | ServiceOrder → **Engagement** → Campaign / Project / Assignment |
| `fulfillment` | ServiceOrder → **Fulfillment Tasks** → Completed |

Примеры `fulfillment`: разовая консультация, один документ, разовый аудит.  
Примеры `ongoing`: таргетинг, рекрутинг, аутсорсинг, консалтинг на период.

### 8.2 Engagement

Таблица `engagements` (MVP — минимальный shell):

| Поле | Назначение |
|------|------------|
| `service_order_id` | Родительский заказ |
| `engagement_type` | `campaign` \| `project` \| `recruitment_assignment` \| `support_case` |
| `status` | `setup` \| `waiting_for_client` \| `ready_to_launch` \| `active` \| `optimization` \| `paused` \| `completed` \| `cancelled` |

Внутри Engagement — доменные дочерние объекты (Campaign, Project, …) по мере зрелости модулей.

---

## 9. Decision: Finance bindings (MVP)

| Объект | Связь |
|--------|-------|
| **Invoice** | `service_order_id`, `company_id` (billing recipient) |
| **Payment** | `invoice_id` → триггер milestone `payment_received` на CommercialConfirmation |

**ADR-004 target:** Invoice из Billing Event. **MVP exception:** прямой путь `Invoice ← ServiceOrder` допустим как legacy-compatible slice; Billing Event — phase 2. Новый код должен эмитить domain events, готовые к миграции на BillingEvent (`ADR-019` action `finance.create_invoiceable_event`).

---

## 10. Canonical end-to-end flow

```text
┌─ SALE ─────────────────────────────────────────────────────────┐
│ Sales Inquiry → [optional Opportunity] → Quote acceptance      │
│ Результат: клиент выразил намерение купить конкретное предлож. │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌─ ORDER & COMMERCE ─────────────────────────────────────────────┐
│ Quote (scope_snapshot) → Service Order (pending_confirmation)    │
│ → Commercial Confirmation (method milestones) → confirmed      │
│ Результат: заказ существует, основание выполнено.              │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌─ ACTIVATION ───────────────────────────────────────────────────┐
│ Readiness checks → activation_allowed                          │
│ Результат: заказ можно передать в исполнение.                  │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌─ DELIVERY ─────────────────────────────────────────────────────┐
│ [optional Engagement] → Campaign / Project / Tasks → Completed │
│ Результат: услуга оказывается и измеряется.                    │
└────────────────────────────────────────────────────────────────┘
```

### Пример: таргетинг, «выставьте счёт»

```text
1. Meta Lead → Sales Inquiry
2. Менеджер: Quote из каталога (paid_invoice policy)
3. Клиент принимает → Quote accepted
4. Service Order (pending_confirmation), scope_snapshot скопирован
5. CommercialConfirmation (paid_invoice): invoice issued
6. Клиент платит → payment_received → confirmation completed → SO confirmed
7. Readiness: meta_access blocking → activation_allowed false
8. Клиент даёт доступ → activation_allowed true → SO ready → active
9. Engagement (campaign) создан (execution_mode=ongoing)
10. Meta leads → route: candidate_application (не новый Sales Inquiry)
```

### Пример: счёт на другое юрлицо

```text
… step 5: клиент указывает Sp. z o.o. X
→ Company создаётся / выбирается
→ billing_company_id на SO
→ Invoice.company_id = X
ClientAccount не меняется.
```

---

## 11. MVP scope

### 11.1 Обязательные объекты

| # | Объект | Статус в коде |
|---|--------|---------------|
| 1 | Sales Inquiry | ✅ есть (Lead facade) |
| 2 | **ClientAccount** | ❌ новая сущность (Stage 1) |
| 3 | **Quote** | ❌ новая сущность |
| 4 | **ServiceOrder** (расширенный lifecycle) | ⚠️ есть, требует полей |
| 5 | **CommercialConfirmation** | ❌ новая сущность |
| 6 | Invoice + Payment | ✅ есть |
| 7 | **ServiceOrderReadinessCheck** | ❌ новая (может быть JSON block) |
| 8 | **Engagement** (shell, conditional) | ❌ новая сущность |

### 11.2 Отложено (phase 2+)

- Opportunity (отдельная сущность)
- ClientAccountPartyLink (party graph)
- Scope как отдельная таблица
- Agreement / Document Hub contract lifecycle
- Universal Onboarding Case (Process Engine)
- Subscription → recurring Service Orders
- Service Period vs Billing Period
- Billing Event (полный ADR-004 path)
- Commercial Confirmation methods: signed_agreement, manual_postpay, Stripe, …

### 11.3 MVP key relations

| Объект | Связи |
|--------|-------|
| Sales Inquiry | `client_account_id` nullable |
| Quote | `client_account_id`, `source_inquiry_id` |
| Service Order | `client_account_id`, `billing_company_id` nullable, `quote_id` nullable |
| Commercial Confirmation | `service_order_id`, `method_code`, `status` |
| Invoice | `service_order_id`, `company_id` |
| Payment | `invoice_id` |
| Engagement | `service_order_id` (если `execution_mode=ongoing`) |

---

## 12. UI Constitution alignment

| UI term | Domain entity | Workspace |
|---------|---------------|-----------|
| Обращение | Sales Inquiry (Lead facade) | `/app/sales` Application |
| Клиент | **ClientAccount** | `/app/clients/:id` Entity |
| Коммерческое предложение | Quote | plugin в Client / Inquiry workspace |
| Заказ | ServiceOrder | `/app/service-orders/:id` Process |
| Юрлицо / реквизиты | Company (party) | section в ClientAccount workspace |

**Запрещено** отображать `Company` как синоним «Клиент» в primary navigation после cutover Stage 1.

Handoff chain (обновлённый):

```text
Sales: Source → Обращение → Клиент (ClientAccount) → Заказ (ServiceOrder)
```

---

## 13. Module ownership

| Entity | Owner module | Notes |
|--------|--------------|-------|
| Sales Inquiry / Lead transport | Recruitment intake + Sales surface | Lead internal only |
| ClientAccount | **Services** (client commercial relationship) | Shared read для Finance portal |
| Quote | **Services** | |
| ServiceOrder | **Services** (ADR-004) | |
| CommercialConfirmation | **Services** (process); Finance validates payment milestones | |
| Invoice / Payment | **Finance** (ADR-004) | |
| Engagement | **Services** | Campaign attribution → Recruitment read |
| Readiness checks (sales domain) | **Services** contributor | Platform contract |
| Company / Contact | **Platform / Companies** | Party registry |

---

## 14. Mapping to current code (technical debt)

| Current | Target | Migration |
|---------|--------|-----------|
| `convert-client` → `Company` only | + parallel `ClientAccount` | Stage 1 wrapper |
| `ServiceOrder.company_id` as client | `client_account_id` + `billing_company_id` | Additive columns; deprecate semantic overload |
| Funnel stage `proposal` | `Quote` entity | Stages remain for Inquiry; Quote is object |
| `invoices/from-service-order` direct | + CommercialConfirmation milestones | MVP keeps direct path; emit events |
| `Company.extra` client fields | `ClientAccount` columns | Strangler migration |
| `client_workspace.py` contract markers | CommercialConfirmation + Readiness | Gradual |

---

## 15. Domain events (ADR-019 hooks)

Минимальный набор для MVP automation plane:

| Event | When |
|-------|------|
| `sales.inquiry.created` | Intake routed to sales |
| `sales.quote.accepted` | Quote → accepted |
| `services.service_order.created` | SO leaves draft |
| `commerce.confirmation.completed` | CommercialConfirmation → completed |
| `services.service_order.activation_allowed` | Readiness gate passed |
| `services.engagement.started` | Engagement → active |
| `finance.payment.received` | Payment recorded |

---

## 16. Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| **A: ClientAccount as view over Company** | Нет стабильного id; поля расползутся по `Company.extra` / Lead / SO |
| **Proposal instead of Quote** | Не масштабируется на Fleet, licenses, equipment |
| **Contract-centric flow** | Блокирует invoice-only SMB path |
| **Opportunity as mandatory gate** | CRM-театр для «выставьте счёт» |
| **Readiness as average %** | Ложные срабатывания запуска |
| **Engagement always required** | Избыточно для fulfillment-услуг |
| **Quote accepted = commercial confirmed** | Смешивает Sale и Commerce для paid_invoice |

---

## 17. Consequences

1. **Новые таблицы (MVP):** `client_accounts`, `quotes`, `commercial_confirmations`, `engagements`; расширение `service_orders`; readiness storage.
2. **`convert-client` меняется:** создаёт ClientAccount + Company; возвращает `client_account_id`.
3. **Sales workspace plugins:** Quote builder, SO creation, readiness rail (Workspace Layer ADR-017).
4. **Finance:** Payment handler обновляет CommercialConfirmation milestones.
5. **Service catalog:** поля `execution_mode`, `default_confirmation_method_code`.
6. **Phase 2:** Opportunity, party links, Billing Events, Subscription, Service Period / Billing Period — отдельные ADR amendments или ADR-021.
7. **Документы для обновления в PR имплементации:** `docs/services/module-scope.md`, `ui-constitution-v1.md` §2, `hostflow-core-domain-map-v1.md` ownership row.

---

## 18. References

- [`ADR-004`](ADR-004-five-product-modules-and-billing-events.md) — Services vs Finance; Billing Events (deferred in MVP)
- [`ADR-003`](ADR-003-tenant-company-module-data-boundaries.md) — `owner_company_id`, tenant vs company
- [`ADR-017`](ADR-017-workspace-layer.md) — Service Order / Client workspaces
- [`ADR-019`](ADR-019-automation-capability-entitlement-control-plane.md) — domain events, `finance.create_invoiceable_event`
- [`ui-constitution-v1.md`](ui-constitution-v1.md) — Обращение, Клиент, Заказ
- [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md) — Workspace Readiness platform capability
- [`../../services/module-scope.md`](../../services/module-scope.md) — Services module scope
