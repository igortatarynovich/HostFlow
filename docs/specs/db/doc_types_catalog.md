# 📚 Document Types Catalog

> Канонический справочник типов документов. Любые изменения проводятся через миграции и синхронизацию сидов.

---

## 1. Формат записи

| Поле | Тип | Описание |
|------|-----|----------|
| `code` | text | Уникальный идентификатор (`snake_case`) |
| `kind` | enum(`driver`,`employer`,`process`) | Группа в UI |
| `aliases` | text[] | Допустимые синонимы (для импорта/CSV) |
| `process_type` | enum(...) / null | Пресет workflow (только для `kind=process`) |
| `default_expire_in_days` | int / null | Срок истечения по умолчанию |
| `required_meta` | text[] | Дополнительные обязательные поля (`meta`) |
| `owner_summary_weight` | smallint | Вес в отчёте (для расчёта «температуры») |
| `i18n_key` | text | Ключ перевода (`documents.catalog.<code>`) |
| `is_active` | bool | Управление доступностью |

---

## 2. Каталог (v1.0)

| code | kind | aliases | process_type | default_expire_in_days | required_meta | owner_weight |
|------|------|---------|--------------|------------------------|---------------|--------------|
| `identity_document` | driver | `passport`, `id_card` | — | 3650 | `country`, `number` | 50 |
| `driver_license` | driver | `license`, `cat_ce` | `driver_license_exchange` | 1825 | `country`, `categories` | 60 |
| `qualification_code95` | driver | `code95` | — | 1825 | `issuer` | 40 |
| `medical_certificate` | driver | `med_cert` | — | 365 | `issuer`, `facility` | 30 |
| `criminal_record` | driver | `no_criminal_history` | — | 365 | `issuer` | 20 |
| `bank_account_confirmation` | driver | `bank_statement` | — | null | `iban` | 10 |
| `pesel` | driver | `national_number` | — | null | `number` | 10 |
| `contract` | employer | `employment_contract` | — | null | `company_id`, `role` | 40 |
| `assignment` | employer | `delegation` | — | null | `route` | 30 |
| `insurance` | employer | `ubezpieczenie` | — | 365 | `policy_number` | 20 |
| `bhp` | employer | `safety_training` | — | 365 | `issued_by` | 20 |
| `accommodation` | employer | `housing` | — | 365 | `address` | 10 |
| `work_permit` | process | `zezwolenie_na_prace` | `work_permit` | null | `voivodeship`, `type` | 70 |
| `visa` | process | `visa_type` | `visa` | null | `country`, `category` | 60 |
| `residence_card` | process | `karta_pobytu` | `residence_card` | null | `voivodeship` | 60 |
| `swiadectwo_kierowcy` | process | `driver_attestation` | `swiadectwo_kierowcy` | null | `issuer_country` | 50 |
| `tachograph_card` | process | `card_tacho` | `tachograph_card` | 1825 | `country` | 50 |
| `driver_license_exchange` | process | `exchange` | `driver_license_exchange` | null | `from_country` | 40 |
| `other` | any | `custom` | — | null | `custom_name` | 0 |

> Поле `owner_summary_weight` используется для расчёта сводки по документам (см. `documents.md`). Чем выше вес, тем выше влияние отсутствия/просрочки.

---

## 3. Политика `doc_type = 'other'`

- Требует обязательного заполнения `custom_name` (последовательность символов 3–120).
- В UI отображается как введённое название.
- Дополнительно можно указать `custom_alias` для импорта CSV (Tenant Admin Console).
- Такие документы не участвуют в автоматических отчётах, пока явным образом не назначен `owner_summary_weight`.

---

## 4. Управление и миграции

- Добавление нового типа → Alembic миграция + обновление сидов (`backend/app/db/seeds`).
- Изменение `default_expire_in_days` не затрагивает существующие документы (только новые).
- Деактивация `is_active=false` скрывает тип из UI, но не удаляет существующие записи.
- Тесты должны проверять синхронизацию каталога (см. `tests/documents/test_catalog.py`).
