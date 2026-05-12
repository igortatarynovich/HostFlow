

# HostFlow — LLM Agent Startup Prompt (Команда‑запуск)

**Роль:** Ты — системный LLM‑агент HostFlow. Работаешь как архитектор и документатор.  
Следуешь правилам из `edit_protocol.md`: delta‑only, один файл за раз.  
Используешь контекст из `context_map.yml`, мини‑файлы (`.min.md`) и сниппеты (`_llm/snippets/*`).  
Термины берёшь из `abbreviations.yml`.

---

## 🎯 Конечная цель
Создать и поддерживать масштабируемую, документированную экосистему **HostFlow** (SaaS, multi‑tenant) для транспортного сектора.  
Все изменения должны усиливать связность системы и не ломать инварианты RLS, RBAC, API и Ruleset.

---

## 🧱 Инварианты
- RLS, RBAC, Audit — неизменяемы.
- Tenant‑aware API (`/api/v1/*`), унифицированные статусы и события.
- Документированность: каждое изменение сопровождается обновлением `/docs/specs/*`.
- Минимизация токенов — через `.min.md`, `.snip`, `context_map.yml`.

---

## 🔄 Приоритетные домены
1. **Core → Company Profile** (companies)
2. **Finance → Invoicing / Payments**
3. **Portals → Client / Candidate**
4. **Automation → Scheduler / Approvals / AI**
5. **Integration & Observability**

---

## ⚙️ Общие правила работы
- Один файл → одна операция (≤ 700 токенов).
- Все изменения — delta‑diff.
- Длинные блоки выноси в сниппеты.
- Добавляя или изменяя якоря — обновляй `context_map.yml`.

---

## ✅ Checklists
- **Core:** `core.md` включает разделы Expansion, Layers, Scaling, DevOps.
- **Rules:** обновлены разделы 19–25.
- **Companies:** существует `company_profile.md`; требуется расширение.
- **Finance:** есть `schema_invoicing.sql`, `invoicing.min.md`.
- **Portals:** candidate/client portals готовы.
- **Scheduler:** присутствует `scheduler.md` и сниппеты уведомлений.

---

## 🚀 Стартовая задача (первая итерация)
**Домен:** Core → Company Profile (Companies)

**Цель:** выровнять и расширить Company Profile так, чтобы он стал единым источником истины для юридических, платёжных и операционных данных компании.  
Подготовить структуру для Invoicing, Contracts, Portals, Providers и Compliance.

**Файл 1 (цель правки):** `/docs/specs/modules/company_profile.md`

**Действие:** Добавить новые подразделы «Canonical Data Model» и «API & Validation Matrix» (без дублирования существующих разделов).

**Delta‑инструкция (шаблон):**
```
<instructions>
- В файле `/docs/specs/modules/company_profile.md` после первого уровня заголовков добавь:

## Canonical Data Model
- **Legal Entity:** `legal_name`, `reg_no`, `tax_id`, `vat_eu`, `established_at`, `registered_address{country,city,street,zip}`.
- **Billing:** `default_currency`, `payment_terms_days`, `billing_address{...}`, `invoice_email`, `einvoice_peppol`.
- **Banking:** `bank_accounts[]` → `{iban, swift_bic, bank_name, is_primary}`.
- **Contacts:** `contacts[]` → `{role(OWNER/ACC/HR/FM), full_name, email, phone, is_primary}`.
- **Operational Profile:** `fleet{tractors,intl_perc,local_perc}`, `trailers{mega,standard,frigo,container}`, `lanes{origins[],destinations[]}`, `cargo_types[]`.
- **Compliance:** `fin_check_status`, `aml_required`, `iso9001`, `insurance_policy_no`, `doc_valid_until`.
- **Integrations:** `provider_ids[]`, `webhooks{...}`, `branding{logo_url,primary_color}`.

## API & Validation Matrix
- `POST /companies` → создаёт базовую карточку; валидирует `legal_name`, `tax_id`, `country`.
- `PATCH /companies/{id}/legal` → редактирует **Legal Entity**; `tax_id` формат по стране.
- `PUT /companies/{id}/billing` → **Billing** + `payment_terms_days`(1–120).
- `POST /companies/{id}/bank-accounts` → IBAN checksum; один `is_primary=true`.
- `POST /companies/{id}/contacts` → роль из enum; один `is_primary=true`.
- `PUT /companies/{id}/operations` → обновляет **Operational Profile**.
- `GET /companies/{id}/readiness` → агрегированный статус для контрактов/инвойсинга.
- Ошибки: `422 LEGAL-TAXID`, `422 IBAN-CHECK`, `409 CONTACT-PRIMARY`, `403 RBAC`, `409 BANK-PRIMARY-EXISTS`.
</instructions>
```

**Далее:**
- `/docs/specs/db/schema_companies.sql` → добавить таблицы `company_bank_accounts`, `company_contacts`, `company_operations`.
- `/docs/specs/api/companies.http` → обновить примеры legal/billing/banking/contacts/operations.
- `/docs/specs/min/companies.min.md` → мини‑конспект Company Profile.
- `/docs/specs/rules.md` → добавить проверки NIP/IBAN/primary-contact.
- `/docs/_llm/context_map.yml` → обновить якоря company_profile.

---

## 📦 Формат итераций
```
Goal → Changes (diff) → Affected IDs/Files → Next steps
```

---

## 🧭 Финальная проверка
- Company Profile согласован между модулями, схемами и API.
- Информация используется в Invoicing, Contracts, Providers.
- Все якоря добавлены в `context_map.yml`.
- Нет дублирования — только ссылки на сниппеты.