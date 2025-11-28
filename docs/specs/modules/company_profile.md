# Company Profile (Профиль компании)

## Цель
Расширить карточку компании, превратив её в полноценный CRM/ERP-профиль транспортной компании с юридическими, финансовыми и операционными данными, контрактами и историей заказов.

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
- `PATCH /companies/{id}` → обновляет плоские поля карточки (название, телефон, адрес, заметки, архив).
- `PATCH /companies/{id}/legal` → редактирует **Legal Entity** (адреса, лицензии, представители).
- `PUT /companies/{id}/billing` → сохраняет **Billing** и проверяет `payment_terms_days` ∈ [1;120], email и IBAN.
- `POST`/`PATCH`/`DELETE /companies/{id}/bank-accounts` → CRUD по счетам; допускается только один `is_primary=true`.
- `POST`/`PATCH`/`DELETE /companies/{id}/contacts` → контакты (`OWNER`, `ACC`, `HR`, `FM`, `OPS`, `LEGAL`, …); единственный `is_primary=true`.
- `PUT /companies/{id}/operations` → обновляет **Operational Profile** (флоты, маршруты, языки, гражданства).
- `PATCH /companies/{id}/compliance` → статус проверок, `aml_required`, `doc_valid_until`.
- `PATCH /companies/{id}/integrations` → провайдеры, webhooks, бренд.
- `PATCH /companies/{id}/portal`, `POST /companies/{id}/enable-portal` → управление клиентским порталом.
- `GET /companies/{id}/readiness` → агрегированный статус профиля (legal/billing/contacts/compliance/portal).
- Ошибки: `422 IBAN-CHECK`, `409 CONTACT-PRIMARY`, `409 BANK-PRIMARY-EXISTS`, `403 RBAC`.

## Структура профиля
### 1. Юридические данные
| Поле | Описание |
|------|-----------|
| `legal_name` | Полное юридическое название |
| `regon`, `krs`, `nip`, `vat_eu` | Регистрационные номера |
| `address_registered`, `address_operational` | Юридический и фактический адрес |
| `country`, `city`, `postal_code` | Географические данные |
| `founded_at` | Дата регистрации |
| `transport_license_number` | Лицензия на транспортную деятельность |
| `insurance_policy_number` | Номер страховки |

### 2. Банковские и платежные данные
| Поле | Описание |
|------|-----------|
| `bank_name` | Банк |
| `iban`, `swift` | Реквизиты |
| `billing_currency` | Валюта расчётов |
| `payment_terms_days` | Срок оплаты по умолчанию |
| `billing_email` | Email для отправки счетов |
| `billing_address` | Адрес для выставления счетов |
| `bank_accounts[]` | Счета `{id, bank_name, iban, swift_bic, label, is_primary}` |

### 3. Контактные лица
| Поле | Описание |
|------|-----------|
| `contacts[]` | Массив контактов `{id, role, full_name, phone, email, is_primary}` |
| `authorized_representatives[]` | Представители, уполномоченные подписывать контракты |

### 4. Деятельность компании
| Поле | Описание |
|------|-----------|
| `fleet_tractors` | Количество тягачей |
| `fleet_trailers` | Количество прицепов |
| `trailer_types[]` | Типы прицепов (tent, chłodnia, cysterna и т.д.) |
| `routes[]` | Основные направления перевозок (PL, EU, UK, CH, NO и т.д.) |
| `cargo_types[]` | Типы грузов (spożywka, ADR, farmacja и т.д.) |
| `drivers_total` | Общее количество водителей |
| `languages[]` | Рабочие языки компании |
| `preferred_nationalities[]` | Приоритетные гражданства водителей |
| `has_adr_operations` | Признак перевозки опасных грузов |
| `work_modes[]` | Форматы работы (UoP, B2B, lease) |

### 5. Контракты и заказы
- `contracts[]`: связь с таблицей контрактов.
- `company_orders[]`: активные и завершённые заказы (минимум: статус, даты, требуемые/нанятые водители).
- Прогресс по заказам: количество требуемых и нанятых водителей.
- История взаимодействий и комментарии рекрутеров.

### 6. Портал клиента
| Поле | Описание |
|------|-----------|
| `client_portal_enabled` | Включён ли доступ клиента |
| `client_portal_url` | Ссылка на портал |
| `portal_roles[]` | Список пользователей клиента с ролями |
| `permissions` | Настройки доступа и видимости данных |

### 7. Финансовая интеграция
- Связь с модулем **Invoicing**:
  - Генерация счетов на основе контрактов и заказов.
  - Сохранение истории оплат и задолженностей.
- Автоматическое создание профиля в модуле `billing` при создании компании.
- Возможность подключения к бухгалтерским системам (Fakturownia, Subiekt, wFirma).

## API (черновик)
- `GET /companies/{id}` — просмотр карточки.
- `PATCH /companies/{id}` — частичное обновление базовых полей.
- `PATCH /companies/{id}/legal` — раздел Legal Entity.
- `PUT /companies/{id}/billing` — платежные настройки и счета.
- `POST`/`PATCH`/`DELETE /companies/{id}/bank-accounts` — CRUD по банковским счетам.
- `POST`/`PATCH`/`DELETE /companies/{id}/contacts` — CRUD по контактам.
- `PUT /companies/{id}/operations` — операционный профиль.
- `PATCH /companies/{id}/compliance` — статусы проверок.
- `PATCH /companies/{id}/integrations` — провайдеры и webhooks.
- `PATCH /companies/{id}/portal`, `POST /companies/{id}/enable-portal` — портал клиента и права.
- `GET /companies/{id}/readiness` — агрегированная готовность к контрактам/инвойсам.

## Безопасность
- RLS: доступ только в рамках tenant.
- `OWNER` и `RECRUITER` могут редактировать профиль.
- `CLIENT` видит только свою компанию через портал.
- Все изменения логируются в `audit_log`.

## Тест-кейсы
- Создание компании с полными реквизитами.
- Добавление контактных лиц и портала клиента.
- Создание контракта и проверка связи.
- Генерация счёта на основании контракта.
- Проверка RLS: клиент не видит чужие компании.

### Readiness Metrics
- `has_legal` — юридический блок заполнен (регистрация/адрес/представители).
- `has_primary_contact` — назначен основной контакт.
- `has_primary_bank` — есть основной банковский счёт.
- `billing_ready` — настроены валюта, срок оплаты и email для счетов.
- `fin_check_status` — состояние финансовой проверки (`pending`/`pass`/`fail`/`manual_review`).
- `compliance_valid` — документы комплаенса действительны ( `doc_valid_until` ≥ сегодня ).
- `client_portal_enabled` — клиентский портал активирован.
- `readiness_score` — доля выполненных критериев, % (0–100).
