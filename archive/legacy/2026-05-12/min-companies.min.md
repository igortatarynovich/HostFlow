**Companies Module — Summary**

1. **Purpose**  
   Централизованная карточка клиента (transport company) — юридические данные, биллинг, банковские реквизиты, контакты, операционный профиль.

2. **Canonical Data**  
   - Legal Entity: `legal_name`, `reg_no`, `tax_id`, `vat_eu`, `registered_address{country,city,street,zip}`.  
   - Billing: `default_currency`, `payment_terms_days(1-120)`, `billing_address{...}`, `invoice_email`, `einvoice_peppol`.  
   - Banking: `bank_accounts[]` `{iban, swift_bic, bank_name, is_primary}` (один primary).  
  - Contacts: `contacts[]` `{role ∈ OWNER|ACC|HR|FM|OPS|LEGAL|DISPATCH|SALES|SUPPORT|CEO, full_name, email, phone, is_primary}`.  
   - Operations: `fleet_tractors`, `fleet_intl_perc`, `fleet_local_perc`, `trailers{...}`, `lanes{origins[],destinations[]}`, `cargo_types[]`, `languages[]`, `preferred_nationalities[]`, `has_adr_operations`, `work_modes[]`.  
   - Compliance & Integrations: `fin_check_status`, `aml_required`, `iso9001`, `insurance_policy_no`, `doc_valid_until`, `provider_ids[]`, `webhooks[]`, `branding{logo_url,primary_color}`.

3. **API Surface**  
   - `POST /companies` — создание карточки (валидация `legal_name`, `tax_id`, `country`).  
  - `PUT /companies/{id}` (также `PATCH` для обратной совместимости) — базовые поля карточки, архивирование.  
  - `PATCH /companies/{id}/legal` — обновление Legal Entity.  
   - `PUT /companies/{id}/billing` — биллинг и e-invoicing.  
   - `POST /companies/{id}/bank-accounts` — IBAN checksum, единственный primary.  
   - `POST /companies/{id}/contacts` — роль из enum, единственный primary контакт.  
   - `PUT /companies/{id}/operations` — операционный профиль и compliance.  
   - `GET /companies/{id}/readiness` — агрегированный статус (legal/billing/bank/contact/compliance).

4. **Rules & RLS**  
   - tenant isolation (`tenant_id`, RLS политики на все таблицы).  
   - Uniqueness: `(tenant_id, tax_id)`, `(company_id, is_primary=true)` для контактов/счетов.  
   - Проверки: `payment_terms_days` 1–120, `default_currency` ISO 4217, IBAN длина 15–34, email содержит `@`.  
   - Готовность компании влияет на доступность контрактов, инвойсинга, портала клиента.
