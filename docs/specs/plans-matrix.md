# Plans Matrix — Канонический справочник тарифов HostFlow

**Назначение:** единственный источник правды о том, что включено в каждом плане. Любое расхождение между этим документом и кодом — баг: CI ловит его тестом `backend/tests/test_plan_matrix_consistency.py` (Phase 2 #2.1.B в `docs/HOSTFLOW_AUDIT_AND_PLAN.md`).

**Связи:**

- SSOT: `docs/SSOT.md` §2.16 (тарифные пакеты), §2.17 (биллинг-операционка), §2.18 (Stripe-инвентарь).
- Backend константы: `backend/app/api/v1/settings/billing/_helpers/plans.py` (`PLAN_CODES`, `PLAN_LICENSE_LIMITS`, `_available_plans`), `backend/app/services/plan_feature_gates.py`, `backend/app/services/lead_quota.py`, `backend/app/services/portal_candidate_usage.py`, `backend/app/services/tenant_quota.py`, `backend/app/services/billing_restrictions.py`.
- Frontend: `hostflow-frontend/src/hooks/useTeamTierFeatures.ts`, `useLicenseStatus.ts`, `contexts/PlanLimitModalContext.tsx`.

**Терминология:**

- **Внутренний код плана** (`plan_code`): `starter`, `team`, `pro`, `enterprise` (TODO 2.1.C). Используется в `TenantLicense.plan`, в Stripe metadata, в проверках кода.
- **Маркетинговое имя:** `Solo`, `Team`, `Business`, `Enterprise`. Только в UI и лендинге.
- **Trial:** мета-статус `subscription.status='trial'` (продуктово **30 дней**). Feature-gates = Team+/Business depth (`plan_bucket_for_limits('trial') → pro`); soft abuse-caps — `trial_usage_caps` (leads / conv-actions / portal / automation runs).

---

## 1. Тарифы — обзорная таблица

| Внутр. код | UI имя | Цена / мес (€) | Yearly /мес (€) | Кому | Где в коде |
|------------|--------|----------------|-----------------|------|------------|
| `starter` | **Solo** | 29 | 24 | Один пользователь, до ~200 лидов/мес. Тест-драйв продукта. | `_available_plans()` |
| `team` | **Team** | 129 | 109 | До 3 рекрутёров, агентство в начале роста. | `_available_plans()` |
| `pro` | **Business** | 249 | 219 | До 10 пользователей, multi-company, automation, branded portal. | `_available_plans()` |
| `enterprise` | **Enterprise** | по запросу | — | SLA, on-prem, SSO, кастомные интеграции. | Contact-sales only (не self-serve checkout). |

`PLAN_CODES` (источник): `("starter", "team", "pro", "enterprise")`.

---

## 2. Лимиты на seats и базовые сущности

(Источник: `PLAN_LICENSE_LIMITS` в `_helpers/plans.py`. `LICENSE_ADDON_MERGE_FIELDS` показывает, какие из этих лимитов можно расширять add-on-pack-ами.)

| Лимит | Solo | Team | Business | Enterprise | Add-on? | Where enforced |
|-------|------|------|----------|------------|---------|----------------|
| `max_recruiters` | 0 | 2 | 7 | 25 | ✓ | seats invite (TODO ссылка на сервис) |
| `max_supervisors` | 0 | 1 | 3 | 10 | ✓ | seats invite |
| `max_client_managers` | 0 | 0 | 0 | 5 | ✓ | seats invite |
| `max_viewers` | 0 | 0 | 0 | 50 | ✓ | seats invite |
| `max_storage_gb` | 5 | 50 | 200 | 1 000 | ✓ (`pack_storage_50gb`) | `tenant_quota.ensure_storage_*` |
| `max_companies` (своих) | 1 | 1 | 3 | 10 | ✓ (extra workspace slot) | `tenant_quota.ensure_*` |
| `max_candidates_active` | 300 | 2 000 | 10 000 | 50 000 | ✓ (`pack_active_records_2000`) | `tenant_quota.ensure_active_candidate_quota` (TODO 2.1.E: должен считать `leads + candidates + clients`) |
| `max_vacancies_active` | 5 | 50 | 500 | 5 000 | — | `tenant_quota.ensure_open_vacancy_quota` |
| `max_documents` | 1 000 | 10 000 | 100 000 | 500 000 | — | `tenant_quota.ensure_document_quota` |
| `max_public_portal_links` | 0 | 3 | 25 | 100 | ✓ (`pack_client_portal_5`) | portal share creation |

---

## 3. Месячные квоты

| Квота | Solo | Team | Business | Enterprise | Add-on? | Where enforced |
|-------|------|------|----------|------------|---------|----------------|
| Inbound leads / месяц | 200 | 1 500 | 5 000 | 5 000 | ✓ (`pack_leads_500`) | `lead_quota.ensure_monthly_lead_creation_allowed` |
| Active portal candidates / месяц | — | 300 | 2 000 | 2 000 | ✓ (`pack_portal_candidates`) | `portal_candidate_usage.monthly_cap_for_plan_code` |
| Trial-кап (отдельно) | leads 50, conv-actions 20, portal shares 2, automation runs 5 | — | — | — | — | DONE (v1): `lead_quota`=50, `portal_candidate_usage`=2, summary=`trial_caps`; `conversion_actions` и `automation_runs` ограничиваются через `tenant_usage` counters. |

---

## 4. Фичи (вкл./выкл. по тарифам)

(Источник: `plan_feature_gates.py` + `useTeamTierFeatures.ts`. «Team-tier features» = всё, что закрыто для `_TEAM_TIER_BLOCKED_PLANS = {starter, free, solo}`. **Trial (30 дней) намеренно разблокирован** — полный продуктовый контур для оценки; soft abuse-caps остаются в `trial_usage_caps`.)

| Фича | Solo | Trial (30d) | Team | Business | Enterprise | Where enforced |
|------|------|-------------|------|----------|------------|----------------|
| **Лиды — Meta intake** | ✓ (1 credential, 25 mapping rules) | ✓ unlim | ✓ unlim | ✓ unlim | ✓ | `ensure_meta_lead_*` |
| **Лиды — Meta OAuth quick-connect** | ✗ | ✓ | ✓ | ✓ | ✓ | `ensure_meta_leads_oauth_allowed` |
| **Лиды — Generic JSON inbound webhook** | ✗ | ✓ | ✓ | ✓ | ✓ | `ensure_leads_generic_inbound_webhook_allowed` |
| **Лиды — Custom field definitions (active, non-system)** | 10 | unlim | unlim | unlim | unlim | `ensure_lead_custom_field_definition_create_allowed` (+ pack `pack_custom_fields_25/100`) |
| **Лиды — Lead forms (active)** | 0 | base + pack | base + pack | base + pack | base + pack | `lead_forms_quota` (+ `pack_lead_forms_5`) |
| **Лиды — Per-plan source limit (1 / 3 / 10)** | 1 | 10 | 3 | 10 | 10 | DONE: `ensure_lead_source_limit` + create-time enforcement в meta credentials / generic webhook / active lead forms. |
| **Funnel definitions (custom pipelines)** | 1 | 20 | 3 | 20 | 20 | `ensure_custom_funnel_create_allowed` |
| **Communication channels (suммарно)** | 1 | 10 | 3 | 10 | 10 | `ensure_communication_channel_account_create_allowed` |
| **Automation rules (enabled)** | ✗ (no rules at all) | 50 | 10 | 50 | 50 | `ensure_automation_rules_*` (+ `pack_automation_rules_10/25`) |
| **NBA (Next Best Action) / lead distribution рекомендации** | базовые | расширенные (`plan_is_pro_tier` bucket) | базовые | расширенные (`plan_is_pro_tier`) | расширенные | `_nba.py` / lead_distribution upsells |
| **Branded portal per workspace** | ✗ | ✗ | ✗ | ✓ (доп. SKU) | ✓ | (Stripe SKU `branded_portal_per_workspace`) |
| **Client portal per account** | ✗ | ✓ (как Team+) | ✓ (3) | ✓ (25) | unlim | `max_public_portal_links` + `pack_client_portal_5` |
| **Финансы — Invoices** | базовые | базовые | базовые | расширенные (TODO: явный гейт) | расширенные | TBD — **сейчас гейт через 402 в API, без явной плашки.** |
| **SSO / SAML / SCIM** | ✗ | ✗ | ✗ | ✗ | ✓ | TBD (Enterprise-only) |
| **Audit log retention > 90 дней** | 30 d | 90 d | 90 d | 365 d | unlim | TBD |

---

## 5. Add-on packs (Stripe SKU)

(Источник: `ADDON_PACK_CHECKOUT_READY` в `_helpers/plans.py` + `backend/app/services/stripe_price_catalog.py`.)

| SKU | Что добавляет | На каких планах продаётся | Where merged |
|-----|---------------|---------------------------|--------------|
| `pack_portal_candidates` | +N portal candidates / месяц | Team+ (требует `monthly_cap_for_plan_code(plan) is not None`) | `portal_monthly_cap_addon_v1` |
| `pack_client_portal_5` | +5 public portal links | все платные | `max_public_portal_links_delta` |
| `pack_automation_rules_10` / `_25` | +10 / +25 enabled rules | Team+ | `automation_rules_enabled_cap_addon` |
| `pack_custom_fields_25` / `_100` | +25 / +100 lead custom fields | **Только Solo** (на Team+ уже unlim) | `lead_custom_field_definitions_cap_addon` |
| `pack_lead_forms_5` | +5 active lead forms | все платные | `lead_forms_active_cap_addon` |
| `pack_leads_500` | +500 inbound leads / мес | все платные | `monthly_leads_cap_addon` |
| `pack_active_records_2000` | +2 000 active records (candidates по факту) | все платные | `max_candidates_active_delta` |
| `pack_storage_50gb` | +50 GB storage | все платные | `max_storage_gb_delta` |

---

## 6. Trial / Past-due / Expired — поведение системы

| Состояние | Что можно | Что нельзя | Where enforced |
|-----------|-----------|------------|----------------|
| **Trial** (`subscription.status='trial'`, до 30 дней) | Team+/Business feature depth (Meta OAuth, webhooks, automation, …) + soft `trial_usage_caps` | После истечения — billing restrictions | `plan_feature_gates` (trial не в `_TEAM_TIER_BLOCKED_PLANS`), `trial_usage_caps`, `billing_restrictions` |
| **Active** | По текущему `plan_code` | — | — |
| **Past_due** (Stripe) | Чтение, экспорт, оплата; завершение текущих задач; закрытие существующих кандидатов (2.1.G v1) | Прочие side-effect write (создание лидов, исходящие comms, automation, non-terminal candidate edits) | `billing_restrictions.ensure_billing_*_allowed` + action-level allowlist |
| **Canceled / Expired** | Только просмотр истории + оплата | Любые мутации, любые исходящие | `billing_restrictions` + `useLicenseStatus` баннер |

---

## 7. UI surface (где пользователь видит что у него есть)

| Где | Что показано | Источник данных |
|-----|--------------|-----------------|
| `/app/settings/billing` (текущий) | Plan card + usage caps + addon offers | `GET /api/v1/settings/billing/summary` (`_available_plans`, `_billing_usage_caps`) |
| `/app/settings/billing/plan` (**TODO 2.1.H**) | Полная таблица «фичи × планы» с пометкой «у тебя сейчас» + Upgrade-CTA | TODO endpoint, derived из этого markdown'а |
| `PlanLimitModal` (контекст) | «Эта функция требует Team+. Купить → Stripe Checkout» | `usePlanLimitModal()` + ответ 402/403 от backend |
| Soft-banner (TODO 2.1.J) | «Вы использовали 80 % лимита X на месяц» | `summary._billing_usage_caps` + порог |

---

## 8. Чего нет в коде (gap vs SSOT)

Следующие пункты SSOT упоминаются в §2.16–§2.18, но не реализованы или реализованы частично. Каждая строка — будущий todo (Phase 2 / Phase 6):

1. `enterprise` как first-class plan_code — **DONE** (contact-sales only, без self-serve checkout).
2. Trial-капы по SSOT (50 / 20 / 2 / 5) → **2.1.D**.
3. Aggregate active records (`leads + candidates + clients`) — **DONE (2.1.E)**: enforced in `tenant_quota.ensure_active_records_quota`.
4. Per-plan lead source limits (1 / 3 / 10) — **DONE (2.1.F)**.
5. Past-due fine-grained whitelist — **DONE (2.1.G v1)**.
6. UI plan-comparison page → **2.1.H**.
7. Unified `PlanLimitModal` copy → **2.1.I**.
8. Soft 80 % banner → **2.1.J**.
9. Stripe Tax + VIES + tax IDs (SSOT §2.18) → Phase 6 backlog.
10. Customer Portal вместо самописного UI (SSOT §2.18) → Phase 6.
11. SKU-based seats / extra channel / extra source / branded portal — есть в Stripe catalog, но нет UI и сквозного enforcement → Phase 6.
12. Audit log retention per plan → нет; нужна tier-based retention policy.
13. SSO / SAML / SCIM (Enterprise) → ничего нет → Phase 6/Enterprise track.

---

## 9. Как обновлять этот документ

1. Любое изменение лимита/фичи в коде сопровождается PR в этот файл.
2. CI-test `backend/tests/test_plan_matrix_consistency.py` парсит таблицы §2 и §3 (и цены из §1) и сверяет с константами — расхождение фейлит билд.
3. Маркетинговые материалы (`docs/pipedesign.md`, лендинг) ссылаются ТОЛЬКО на этот файл.
