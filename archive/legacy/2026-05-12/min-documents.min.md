**Documents Module — Summary**

1. **Purpose**  
   Единая система контроля документов кандидата/работодателя с шаблонами, напоминаниями и workflow.

2. **Core Entities**  
   - `documents`: ключевые поля `kind`, `doc_type`, `status`, `issue_date`, `expire_date`, `workflow`, `meta`, `files`.  
   - `document_templates`: JSON-наборы обязательных документов по типам вакансий (`driver_ce`, `warehouse` и т.п.).

3. **Categories**  
   - Driver — паспорта, права, Code95, тахокарта, PESEL, страховка, банковские данные.  
   - Employer — договор, наряд, страховка работодателя, BHP, проживание.  
   - Process — виза, разрешение на работу, карта pobytu, świadectwo kierowcy, обмен прав.

4. **Statuses & Flow**  
   - Линейка: `missing → requested → in_progress → received → approved/rejected → expired`.  
   - Загрузка файла даёт `received`, финальный шаг workflow — `received` или `approved`.  
   - Просрочка `expire_date` переводит в `expired`.

5. **Workflow**  
   - JSON с шагами (`ordered_at`, `submitted_at`, `approved_at`, `delivered_at` и т.д.).  
   - Поддерживаются пресеты для `work_permit`, `visa`, `residence_card`, `tachograph_card`, `driver_license_exchange`, `swiadectwo_kierowcy`.

6. **Automation**  
   - Шаблон выбран в UI → чек-лист документов создаётся автоматически, PESEL добавляется всегда.  
   - Напоминания и статусы пересчитываются ежедневно (`remind_days_before`, `workflow.steps[*].due_at`).

7. **APIs**  
   - `GET /api/v1/documents?candidate_id=` — выдаёт документы с новыми полями.  
   - `POST /api/v1/candidates/{id}/documents/apply-template` — накладывает шаблон.  
   - `PATCH /api/v1/documents/{id}` — обновляет статус, workflow, даты, файлы.

8. **Security**  
   - RLS по `tenant_id` для `documents` и `document_templates`.  
   - Только менеджеры/админы могут создавать/обновлять документы.  
   - Все операции логируются и запускают пересчёт напоминаний.
