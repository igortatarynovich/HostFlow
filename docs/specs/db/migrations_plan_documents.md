# Migrations Plan — Documents Module Restructure

## Overview
Миграция переводит существующую таблицу `documents` на новую схему и добавляет таблицу `document_templates`. Все операции выполняются для PostgreSQL с учётом RLS (`tenant_id`).

## Steps

1. **Enums**
   - `document_kind_enum`: `driver`, `employer`, `process`.
   - `document_status_enum_v2`: `missing`, `requested`, `in_progress`, `received`, `approved`, `rejected`, `expired`.
   - `document_requested_from_enum`: `driver`, `employer`, `agency`.
   - `document_process_type_enum`: `none`, `work_permit`, `visa`, `residence_card`, `tachograph_card`, `driver_license_exchange`, `swiadectwo_kierowcy`, `other`.

2. **documents table changes**
   - Add columns: `company_id UUID`, `kind document_kind_enum NOT NULL DEFAULT 'driver'`, `doc_type TEXT NOT NULL DEFAULT 'identity_document'`, `custom_name TEXT`, `status document_status_enum_v2 NOT NULL DEFAULT 'missing'`, `issue_date DATE`, `expire_date DATE`, `requested_from document_requested_from_enum DEFAULT 'driver'`, `process_type document_process_type_enum NOT NULL DEFAULT 'none'`, `workflow JSONB`, `meta JSONB`.
   - Rename/migrate:  
     - `issued_at` (timestamptz) → `issue_date` (date).  
     - `expires_at` (timestamptz) → `expire_date` (date).  
     - `extra`/`meta_json` → `meta`.  
     - `type` → `doc_type` (оставить совместимость через VIEW или триггер).  
   - Optional cleanup: оставить `number`, `filename`, `path`, `source`, `external_id` до полной декомиссии.

3. **Data backfill**
   - `doc_type`: брать из старого `type`; fallback на `meta_json["doc_type"]` или `'identity_document'`.
   - `kind`: вычисляется по `doc_type` (см. таблицу ниже).
   - `status`: маппинг `planned→missing`, `pending_validation→in_progress`, `verified→approved`, `invalid→rejected`, `expired→expired`, остальные → `requested`.
   - `issue_date` / `expire_date`: `DATE(issued_at)` и `DATE(expires_at)`.
   - `meta`: объединить `extra` и `meta_json`, добавить `{"legacy_number": number}` если `number` не пуст.
   - `requested_from`: по умолчанию `driver`, но для employer-документов — `employer`.
   - `process_type`: по doc_type (`work_permit`, `visa`, `residence_card`, `swiadectwo_kierowcy`, `tachograph_card`, `driver_license_exchange`; иначе `none`).

4. **Kind mapping**

| doc_type                     | kind     | requested_from default | process_type        |
|------------------------------|----------|------------------------|---------------------|
| `identity_document` (`passport`, `national_id`, `id_card`) | driver | driver | none |
| `driver_license` (`prawo_jazdy`) | driver | driver | none |
| `qualification_code95` (`code95`, `code_95`) | driver | driver | none |
| `medical_certificate` (`badania_lekarskie`, `medical`) | driver | driver | none |
| `criminal_record` | driver | driver | none |
| `photo` (`photo_id`) | driver | driver | none |
| `bank_account_confirmation` (`bank_account_doc`) | driver | driver | none |
| `pesel` (`pesel_confirm`) | driver | driver | none |
| `contract` (`employment_contract`, `umowa_o_prace`) | employer | employer | none |
| `assignment` (`work_assignment`, `oswiadczenie`) | employer | employer | none |
| `insurance` (`insurance_a1`, `employer_insurance`, `insurance_confirmation`) | employer | employer | none |
| `bhp` (`bhp_instruction`, `szkolenia_BHP`) | employer | employer | none |
| `accommodation` (`accommodation_declaration`) | employer | employer | none |
| `work_permit` (`zezwolenie_A`) | process | agency | work_permit |
| `visa` (`visa_D`, `entry_permit_or_visa`) | process | driver | visa |
| `residence_card` (`karta_pobytu`) | process | driver | residence_card |
| `swiadectwo_kierowcy` (`driver_attestation`) | process | agency | swiadectwo_kierowcy |
| `tachograph_card` (`karta_tachografu`, `tachograph_exchange`) | process | agency | tachograph_card |
| `driver_license_exchange` | process | agency | driver_license_exchange |
| `other` | driver | driver | other |
| `other` | (по вводу) | (по вводу) | `other` |

5. **document_templates table**
   - Create table с PK, tenant_id, code, name, documents(jsonb), is_active, created_by, created_at, updated_at.
   - Add unique constraint `(tenant_id, code)`.
   - Create GIN index на `documents` при необходимости фильтрации.

6. **Seeds**
   - Insert базовые doc_type обновлёнными кодами.
   - Создать шаблоны `driver_ce` и `warehouse` (см. task spec).
   - Убедиться, что PESEL добавляется во все шаблоны.

7. **Cleanup**
   - Обновить триггеры/вьюхи (`documents_progress`, `documents_summary`) под новые статусы.
   - Добавить partial index `documents (candidate_id, doc_type) WHERE deleted_at IS NULL`.
   - Обновить API/ORM-слой на новые колонки; для старых клиентов предусмотреть fallback.

## Rollback Strategy
1. Создать временные копии столбцов (`doc_type_old`, `status_old` и т.д.) перед обновлением, чтобы можно было вернуть значения.
2. В случае отката удалить новые enum-типы, таблицу `document_templates`, вернуть старые значения колонок.
3. Напоминания и фоновые задачи используют очереди; в rollback необходимо пересоздать расписания.

## Testing
- Прогнать тесты на CRUD документов, применение шаблона и workflow.
- Запустить миграцию на snapshot прод-базы (staging) и сверить количество документов по статусам/категориям.
- Проверить, что RLS-политики работают для новых колонок (`tenant_id` обязателен).
