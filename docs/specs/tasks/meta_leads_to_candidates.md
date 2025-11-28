


# HostFlow: Meta Leads → Candidates Integration (PostgreSQL)

> Статус: ✅ реализовано (webhook `/api/v1/leads/meta`, таблицы `leads`, `meta_ads_map`, `meta_lead_credentials`, `meta_lead_settings`; автоматическое создание кандидатов с fallback-логикой и админкой подключения).

## Цель
Обеспечить автоматическое создание кандидатов из лидов Meta (Facebook/Instagram) с привязкой к нужной вакансии и назначением ответственного рекрутера.  
Проект уже полностью переведён на PostgreSQL — используем все преимущества (jsonb, enum, FK, GIN).

---

## 1. Общая схема

1. Meta Ads → Webhook → `/api/v1/leads/meta`
2. Normalization → Deduplication
3. Vacancy Resolution (`vacancy_id` / `utm` / `ad_id`)
4. Candidate Creation (`vacancy_id`, `tenant_id`, `company_id`, `source='meta'`)
5. Recruiter Assignment (based on `vacancy.owner_id` or pool)
6. Notification → Recruiter
7. Lead status update (`processed` / `duplicated` / `needs_routing`)

---

## 2. Определение вакансии

**Основные способы:**
- В форме Meta передаётся скрытое поле `vacancy_id` (или slug).
- В `utm_campaign` или `utm_content` передаётся `vacancy_<short_id>`.
- Если нет — используется таблица маппинга Meta → Vacancy:
  ```sql
  create table if not exists meta_ads_map (
    ad_id bigint primary key,
    vacancy_id uuid not null references vacancies(id) on delete cascade,
    note text,
    created_at timestamptz default now()
  );
  ```

---

## 3. Создание кандидата

- Антидубль: поиск по email или телефону в рамках `tenant_id` и `company_id`.
- Если найден — статус `duplicated`, `candidate_id` указывает на существующего.
- Если нет — создаётся новый кандидат:
  - `source = 'meta'`
  - `origin = payload`
  - `vacancy_id` определяется по шагу 2
  - `recruiter_id` назначается через алгоритм (см. ниже)

```sql
alter table candidates
  add column if not exists vacancy_id uuid references vacancies(id) on delete set null,
  add column if not exists recruiter_id uuid references users(id) on delete set null,
  add column if not exists source text,
  add column if not exists origin jsonb;
```

---

## 4. Назначение рекрутера

1. Если `vacancies.owner_id` задан → рекрутер = владелец вакансии.
2. Если есть пул рекрутеров вакансии → распределение по least-load / round-robin:
   ```sql
   create table if not exists vacancy_recruiters (
     vacancy_id uuid not null references vacancies(id) on delete cascade,
     user_id uuid not null references users(id) on delete restrict,
     weight int not null default 1,
     is_active boolean not null default true,
     primary key (vacancy_id, user_id)
   );
   ```
3. Если ни одно условие не выполнено → фолбэк: supervisor / administrator компании.

---

## 5. Таблица лидов

```sql
create table if not exists leads (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  company_id uuid not null,
  vacancy_id uuid,
  source text not null default 'meta',
  ad_id bigint,
  payload jsonb not null,
  normalized jsonb,
  status text not null default 'new',  -- new|processed|duplicated|failed|needs_routing
  candidate_id uuid,
  error text,
  last_routed_at timestamptz,
  created_at timestamptz default now()
);
create index if not exists idx_leads_status on leads(status);
create index if not exists idx_leads_vacancy on leads(vacancy_id);
create index if not exists idx_leads_payload_gin on leads using gin (payload);
create index if not exists idx_leads_normalized_gin on leads using gin (normalized);
```

---

## 5.1 Дополнительные таблицы

- `meta_lead_credentials` — зашифрованные секреты и токены Meta (`encrypted_secret`, `access_token`, `ad_account_id`, `page_id`, статус подключения).
- `meta_lead_settings` — tenant-настройки: `default_company_id`, `auto_create_enabled`, `fallback_recruiter_id`, `reroute_after_hours`, `mask_pii_in_logs`, `webhook_url`, диагностические поля (`last_webhook_check_at`, `last_signature_status`).
- Все CRUD операции выполняются через admin API `/api/v1/admin/meta-leads/*`, аудируются и доступны только пользователям с правом `admin.metaLeads`.

---

## 6. API и пайплайн

### `POST /api/v1/leads/meta`
- Принимает сырой вебхук Meta
- Поддерживает верификацию `X-Hub-Signature-256`
- Порядок шагов:
  1. `normalize(payload)` → email, phone, full_name, ad_id, utm, vacancy_hint
  2. `resolve_vacancy(vacancy_hint, ad_id)`
  3. `dedupe()`
  4. `create_candidate()`
  5. `assign_recruiter(vacancy_id)`
  6. `notify_recruiter()`
  7. `update lead.status`
- Если `auto_create_enabled=false`, шаги 4–6 пропускаются, лид переводится в `needs_routing`, фиксируется `last_routed_at`, уведомляется администратор tenant.

### Ответ:
```json
{
  "lead_id": "cf9d4...-...",
  "status": "processed",
  "vacancy_id": "96679ac5-...-0f727f75bf57",
  "candidate_id": "ab12...-...",
  "recruiter_id": "cd34...-..."
}
```

---

## 7. Уведомления
- При успешном создании — рекрутер получает уведомление:
  > Новый кандидат из Meta по вакансии X
- При дубле — сообщение владельцу существующего кандидата.
- При ошибке или `needs_routing` — уведомление админу.

---

## 8. Проверки и тесты
- ✅ Лид с `vacancy_id` → кандидат создаётся и назначается.
- ✅ Лид без контактов → `failed`.
- ✅ Дубликат по email/phone → `duplicated`.
- ✅ Лид по закрытой вакансии → фолбэк на supervisor.
- ✅ 1k лидов за минуту → <2s обработка/лид, без ошибок.

---

## 9. Дальнейшие шаги
- SLA-оповещения (email/Slack) при невыполнении `reroute_after_hours`.
- Автоподтверждение работоспособности вебхука по расписанию (`Meta webhook verify`).
- Поддержка дополнительных источников (TikTok, Website) и унифицированный сторож `lead_mapping_rules`.

---
