# Модуль «Документы» — ЖИВОЙ СПЕК (v0.1)

## 0) Режим работы спека
- Любое изменение логики сначала вносится сюда, затем — в код.
- В конце файла — Changelog с датами и краткими причинами.

## 1) Цели модуля
- Хранить и валидировать документы людей и сущностей (кандидат, компания, вакансия).
- Давать сводный статус готовности (OK / не хватает / истекают).
- Управлять сроками, напоминаниями и проверками (approve/reject с причинами).
- Изолируемый модуль, подключаемый в карточки других модулей.

## 2) Сущности и типы
- **DocumentType**: код, название, описание, для кого (candidate/company/vacancy), правила срока/валидации, обязательность по условиям.
- **Document**: конкретный документ; владелец (entityType+id), статус, файл(ы), даты (issuedAt, expiresAt), ревизии.
- **Attachment**: физический файл/версия.
- **Check** (верификация): решение (approved/rejected/pending), кем и когда, причина.
- **Ruleset** (конфиг по тенанту): JSON-набор правил обязательности и валидации по контексту (гражданство, виза, вакансия и т.п.).

## 3) Статусы документа и сводка владельца
- Документ: `missing` | `uploaded` | `approved` | `rejected` | `expired`.
- Сводка владельца (рассчитываемая): `ok` | `incomplete` | `expiring_soon` | `problems` (+ процент готовности).

## 4) Ключевые функции
1. **Шаблоны типов** (CRUD): создание/изменение/архив; привязка к scope (candidate/company/vacancy).
2. **Генерация чек-листа** по Ruleset и контексту кандидата/вакансии.
3. **Загрузка и версии**: presigned URL → загрузка → фиксация метаданных, версионность.
4. **Валидация меты**: даты, номер (регекс), обязательные поля per type.
5. **Проверка (review)**: uploaded → approved/rejected, причины/категории отказа.
6. **Сроки и напоминания**: расчет `expired` и `expiring_soon` (t-N), создание уведомлений/тасков.
7. **Сводка владельца**: процент готовности + список блокеров (v0.1), экспорт PDF/JSON (v0.2).
8. **Поиск и фильтры**: по типу/статусу/истечению/владельцу/проверяющему/текстовый.
9. **События**: `document.created|updated|deleted`, `document.status.changed`, `document.expiring_soon`, `owner.documents.summary.changed`.
10. **Аудит и безопасность**: лог действий user_id/role/tenant_id, RLS, RBAC.

## 5) Правила (Ruleset)
- JSON-конфиг per tenant. Условия (пример): `citizenship`, `residency_status`, `vacancy.requires_visa`, `country_of_work`.
- Результат: `requiredTypes`, `optionalTypes`, параметры валидности (например, `expiring_soon_threshold_days` по типу).
- Перекрытия: вакансия может добавлять/ужесточать перечень.
- Примеры:
  - UA без карты побыту → Паспорт, Основание въезда/виза, Код 95 (или план), Тахограф (если есть), Świadectwo Kierowcy (по требованию компании).
  - EU → ID/паспорт, Код 95, Тахограф (если есть), медсправка (если требуется вакансией).

## 6) Валидации
- Даты: `issuedAt ≤ today ≤ expiresAt` (если есть), `expiresAt ≥ issuedAt`, иначе `expired`.
- Номера: по регексу в DocumentType (опц.).
- Обязательные поля per type (номер/страна/орган/дата и т.д.).
- Анти-дубликаты: у владельца не более одного `approved` документа данного типа (настраиваемо).

## 7) Роли / разрешения
- OWNER — всё; RECRUITER — CRUD, upload, submit; REVIEWER — approve/reject; VIEWER — read-only.
- Ограничения только в рамках `tenant_id` (RLS). Доп. ограничения по владению кандидатами — по политике модуля «Кандидаты».

## 8) Зависимости от модулей
- Кандидаты: контекст (citizenship, residency_status, assigned_vacancy_id).
- Вакансии: требования к документам.
- Компании: кастомные типы/шаблоны.
- Напоминания/Задачи: получение событий `expiring_soon`, SLA проверки.
- Auth/RBAC: токен/роль/tenant_id.
- Файловое хранилище: presigned URL, доступ.

## 9) Событийная модель
- Backend публикует события с payload: `tenantId`, `documentId`, old/new status, `ownerRef`.
- Front диспатчит `CustomEvent('document:updated', { detail })` после действий.

## 10) Публичный API (черновик)
- `GET /api/documents?ownerType=&ownerId=&typeId=&status=&expiresBefore=&q=&limit=&offset=`
- `POST /api/documents`
- `GET /api/documents/{id}`
- `PATCH /api/documents/{id}`
- `DELETE /api/documents/{id}`
- `POST /api/documents/{id}/upload` (или `GET presign`, затем `POST confirm`)
- `POST /api/{ownerType}/{ownerId}/documents`
- `GET /api/{ownerType}/{ownerId}/documents/summary`
- `GET /api/document-types` | `POST /api/document-types` | `PATCH /api/document-types/{id}` | `DELETE /api/document-types/{id}`
- `GET /api/ruleset` | `PATCH /api/ruleset`

## 11) Модель данных (минимум)
- `document_types(id, tenant_id, code, name, entity_scope, meta_schema, number_regex, default_validity_days, is_active, created_at, updated_at)`
- `documents(id, tenant_id, type_id, owner_type, owner_id, title, status, issued_at, expires_at, meta_json, created_at, updated_at, version)`
- `document_attachments(id, document_id, storage_key, mime, size, checksum, created_at)`
- `document_checks(id, document_id, reviewer_id, decision, reason_code, comment, created_at)`
- `rulesets(id, tenant_id, json, created_at, updated_at)`

## 12) Напоминания и SLA
- Планировщик 1×/сутки: пометки `expired`, флаг `expiring_soon` за t-N (по умолчанию 30).
- SLA: напоминать, если `uploaded` > N часов без решения (per Ruleset).

## 13) Ошибки
- `DOC-001 UnknownType`, `DOC-002 Forbidden`, `DOC-003 InvalidDateRange`, `DOC-004 FileTooLarge`,
  `DOC-005 ValidationFailed(meta)`, `DOC-006 AlreadyApprovedExists`.

## 14) Производительность
- Лимиты на размер файла per tenant.
- Индексы: `(tenant_id, owner_type, owner_id)`, `(tenant_id, type_id)`, `(tenant_id, status)`, `(tenant_id, expires_at)`.
- Пагинация keyset — v0.2.

## 15) I18N/Regulatory
- Поля `issuing_country`, поддержка кириллицы/латиницы.
- Временные зоны — UTC в БД; UI — Europe/Warsaw.

## 16) UI-виджеты (контракты)
- `DocumentsPanel(ownerType, ownerId)` — список/загрузка/ревью.
- `DocumentUploader(allowedTypes, onUploaded)`
- `OwnerDocumentsSummary(ownerType, ownerId)` — бэйдж + прогресс.
- Callbacks: `onStatusChange`, `onChecklistResolved`.

## 17) Тестовое покрытие (минимум)
- Чек-лист: 3 сценария (UA без карты; EU; non-EU с визой).
- Даты/статусы: expired/expiring.
- Approve/Reject + аудит.
- RLS: доступ к чужим данным → Forbidden.
- Сводка: корректный процент готовности.

---

## 18) Расширенные зависимости и контексты
- Модуль «Документы» теперь обрабатывает зависимости из `ruleset.example.json`.
- Поддерживаются типы кандидатов: `driver` и `general`.
- Контекст обязательности документов формируется из комбинации:
  - `candidate` (citizenship, residency_status, type);
  - `vacancy` (routes, requires_adr, employment_mode);
  - `company` (require_med_psych, policies);
  - `tenant` и `global` — базовые настройки.
- Валидация обязательных документов строится по приоритету: `vacancy` → `company` → `tenant` → `global`.
- Добавлены alias-группы документов (`medical_cert`, `psycho_test`, `driver_attestation`, `uk_entry_doc`).
- Механизм **stage gates** блокирует переход по этапам кандидата при отсутствии ключевых документов:
  - `to_stage: work_permit_received` → требует `work_permit`;
  - `to_stage: attestation_ordered` → требует `attestation`;
- `to_stage: to_client_base` → требует `qualification_code95`, `tachograph_card`, `medical_certificate`, `psychotest`;
- `to_stage: departure` → блокирует при истекших `qualification_code95`, `tachograph_card`, `medical_certificate`, `psychotest`.

## 19) Интеграции с другими модулями
- **Contracts & Orders:** при завершении заказа проверяется наличие обязательных документов у каждого кандидата.
- **Invoicing:** генерация счетов возможна только после подтверждения документов.
- **Additional Services:** услуги типа `medical`, `psychotest`, `adr_training` автоматически создают/обновляют документы.
- **Company Profile:** компании могут задавать собственные требования к документам через policies.
- **Client Portal:** клиенты видят статусы документов кандидатов, но не могут их изменять.
- **Candidate Portal:** кандидаты могут просматривать и загружать документы; система уведомляет об истечении сроков.
- **Document Templates:** шаблоны актов, инвойсов и сертификатов могут использовать данные из `documents` и `document_types`.
- **Notifications:** напоминания о скором истечении документов направляются рекрутерам, владельцам и кандидатам (за 30, 14, 7 дней).

## 20) Автоматизация и уведомления
- Планировщик ежедневно помечает документы как `expired` и `expiring_soon` по правилам `validity.expiring_soon_days`.
- Автоматически создаются задачи для рекрутеров, если у кандидата отсутствуют обязательные документы.
- Поддерживаются webhooks и системные события:
  - `document.expired`, `document.expiring_soon`;
  - `document.auto_created` (при завершении услуги);
  - `document.stage_gate_blocked`.
- Механизм уведомлений:
  - Email + WhatsApp (через интеграцию);
  - Push в Candidate/Client Portal;
  - Агрегированные отчёты по истекающим документам ежедневно для ролей `OWNER`, `RECRUITER`.
- При создании новых типов документов выполняется проверка уникальности `code` в рамках `tenant`.
- Добавлен аудит всех автоматических действий: `system_user_id='system'`.

## Changelog
- **2025-10-15 (v0.3):** Добавлены Compliance, Reporting, Bulk Operations и Ruleset Versioning.
- **2025-10-15 (v0.2):** Добавлены зависимости Ruleset, интеграции с модулями, автоматизация и уведомления.
- **2025-09-05 (v0.1):** Базовый каркас функций, правил, зависимостей, API и моделей.

---

## 21) Compliance & Audits
- Создан журнал соответствия `documents_compliance_log` — снапшоты состояния документов на дату.
- Содержит: `tenant_id`, `candidate_id`, `percentage_ready`, `missing_types`, `snapshot_date`.
- Автоматически создаётся ежемесячно и при ручных проверках.
- Экспорт доступен в CSV и PDF.
- Данные используются при аудитах (ISO, IRU, WTT, страховые проверки).
- Политика хранения: 24 месяца, затем автоархив.

## 22) Reporting & Analytics
- Панель аналитики документов доступна для `OWNER` и `RECRUITER`.
- Метрики:
  - Процент кандидатов с полным комплектом документов.
  - Среднее время от загрузки до проверки (`uploaded → approved`).
  - Топ‑5 часто истекающих типов.
  - SLA по ревью (время между `uploaded` и `decision`).
- Поддерживаются фильтры по компании, рекрутеру и типу документа.
- Дашборды можно экспортировать в Excel/PDF.
- Все метрики хранятся в агрегированном виде в `document_metrics_daily`.

## 23) Bulk Operations
- Массовые действия для повышения эффективности рекрутеров:
  - approve/reject нескольких документов.
  - генерация напоминаний и задач для групп кандидатов.
  - массовое обновление статусов (например, при загрузке пакета).
- Bulk‑операции логируются с `bulk_operation_id` и привязкой к инициатору.
- Поддерживаются откаты (rollback) в случае ошибок.

## 24) Ruleset Versioning
- Ruleset хранится с версионностью: `ruleset_versions(id, tenant_id, version, json, created_at)`.
- При пересчёте чек‑листа фиксируется `ruleset_version_id`, чтобы можно было воспроизвести состояние на дату.
- Изменение правил требует комментария (причина обновления).
- В `audit_log` фиксируется дифф JSON между версиями.
- Версия ruleset отображается в UI при просмотре документов кандидата.

---

## 25) Integration with Financial and Compliance Modules
- **Invoicing & Payments:**  
  - Генерация счетов (`invoice`) возможна только для компаний, прошедших `fin_checks` (валидные NIP/REGON/VAT UE).  
  - Оплата возможна только после статуса документов `approved`.  
  - Возвраты (`refunds`) фиксируются как отдельные записи и требуют валидации администратора.  
  - Все изменения статусов `invoice` и `payment` синхронизируются с audit log и webhooks.  
- **E-Signature:**  
  - Подпись обязательна для контрактов, актов и финансовых документов.  
  - Система фиксирует события `signature.requested`, `signature.completed`, `signature.expired`.  
  - Подписи хранятся с цифровыми сертификатами и логируются в `sign_audit`.

---

## 26) Extended Operational Dependencies
- **Logistics:** при изменении этапа кандидата на `Планируем приезд` автоматически создаётся поездка (`logistics_trip`).  
  Завершение поездки обновляет статус на `На базе клиента`.  
  Все расходы и ваучеры передаются в `Invoicing`.  
- **Training:**  
  - После завершения курса создаётся документ типа `certificate`.  
  - Истёкшие сертификаты переводят кандидата в статус `Ожидаем обновление`.  
  - Напоминания отправляются за 30, 14 и 7 дней.  
- **Matching Engine:**  
  - Модуль подбора учитывает статус документов кандидата (score penalized при `missing` или `expired`).  
  - Кандидаты без актуальных обязательных документов не отображаются в выдаче.  
- **Scheduler:**  
  - Используется для планирования медосмотров, психотестов и обучения.  
  - Бронирование создаёт события и слоты, привязанные к документам (например, `medical`, `psychotest`).  
- **Providers Network:**  
  - Провайдеры услуг (медицинские центры, школы, отели) привязываются к документам через `service_id`.  
  - Неактивные провайдеры исключаются из доступных вариантов при заказах и логистике.  

---

## 27) Tachograph, Reporting and AI Extensions
- **Tachograph Integration:**  
  - Данные о нарушениях и времени работы водителя могут автоматически обновлять статусы документов (`rest_compliance`, `work_time_cert`).  
  - Нарушения фиксируются как `document_check` с типом `auto_violation`.  
  - При >3 нарушениях за неделю создаётся запись `compliance_alert`.  
- **Reporting:**  
  - Метрики документов теперь включают KPI по тахографам и обучению.  
  - В отчётах доступна корреляция: «Процент действующих документов vs. производительность водителя».  
  - Агрегированные данные хранятся в `document_metrics_daily` и `tachograph_reports`.  
- **AI-Assisted Validation (Planned):**  
  - Внедрение OCR и автоматического извлечения данных из сканов.  
  - Идентификация несоответствий и подсказки по валидации.  
  - Автогенерация рекомендаций рекрутерам и предупреждений по срокам.  

---

## Changelog
- **2025-10-16 (v0.4):** Добавлены финансовые, логистические, обучающие и AI-интеграции (разделы 25–27).  
