

# Ruleset Versioning (Версионирование правил)

## Цель
Модуль обеспечивает управление версиями правил зависимостей и требований к документам (ruleset) во всех доменах HostFlow.  
Цель — гарантировать воспроизводимость проверок и отчётов, а также прозрачную историю всех изменений.

## Основные функции
- Хранение неизменяемых снапшотов правил с автоинкрементом версии.
- Автоматическое вычисление JSON-диффов между последовательными версиями.
- Привязка конкретной версии к операциям комплаенса, проверкам документов, отчётам и массовым действиям.
- Возможность отката активной версии к любой предыдущей с созданием новой версии-наследника.
- Комментарии, цифровая подпись автора, статус активности и журнал использования.

## Модель данных

Все таблицы находятся в схеме документов и используют префикс `document_ruleset_*`.

### `document_ruleset_versions`
```
id UUID PK
tenant_id UUID (RLS)
version INT (уникален в рамках tenant)
json_data JSONB
comment TEXT NULL
created_by UUID NULL
created_at TIMESTAMPTZ
is_active BOOLEAN (только одна активная на tenant)
signature TEXT (SHA256 от json_data + метаданные)
origin_version_id UUID NULL (указывает на источник при откате)
rollback_comment TEXT NULL
```

### `document_ruleset_diffs`
```
id UUID PK
ruleset_id_from UUID (FK -> document_ruleset_versions.id)
ruleset_id_to UUID (FK -> document_ruleset_versions.id)
diff_json JSONB (структурированный патч в формате jsondiffpatch)
created_at TIMESTAMPTZ
computed_with TEXT (версия инструмента диффа)
```

### `document_ruleset_usage`
```
id UUID PK
tenant_id UUID (RLS)
ruleset_version_id UUID (FK -> document_ruleset_versions.id)
used_in TEXT (compliance|report|checklist|bulk_op|other)
reference_id TEXT NULL (ID сущности/операции)
used_at TIMESTAMPTZ
metadata JSONB NULL (дополнительный контекст)
```

## Логика работы
1. При обновлении правил создаётся запись в `document_ruleset_versions` с автоинкрементом версии и вычисленной подписью.
2. Для пары «предыдущая → новая» версия сохраняется структурированный diff в `document_ruleset_diffs`.
3. Все процессы (комплаенс, onboarding, отчёты, bulk) фиксируют `ruleset_version_id` в своей доменной записи и реплицируют использование в `document_ruleset_usage`.
4. Исторические действия читают ruleset только по связанному идентификатору, даже если текущая активная версия другая.
5. Откат к версии создаёт новую запись, копирующую `json_data` выбранной версии, с заполнением `origin_version_id` и `rollback_comment`. Триггеры обеспечивают единственность активной версии.
6. Поддерживаются глобальные (tenant_id = GLOBAL_TENANT) и локальные версии. Глобальные доступны в режиме read-only для остальных tenant.

## API
Префикс: `/api/v1/db/ruleset`.

- `GET /ruleset` — получить активную версию.
- `PATCH /ruleset` — обновить правила, создав новую активную версию (owner/admin).
- `GET /ruleset/versions` — список версий (с пагинацией, фильтром по is_active).
- `GET /ruleset/versions/{id}` — детальная информация (включая подпись и ссылку на origin).
- `POST /ruleset/versions` — создать черновую версию (без активации) с ручным `activate` флагом.
- `POST /ruleset/versions/{id}/activate` — активировать черновую версию, отключив текущую.
- `GET /ruleset/versions/{id}/diff` — diff против предыдущей активной версии или указанной `compare_to`.
- `POST /ruleset/versions/{id}/rollback` — откат к версии (создаёт новую запись с ссылкой на origin).
- `GET /ruleset/usage` — сводка использования (агрегации по `used_in`, фильтр по периоду).

Все write-операции требуют ролей `administrator` (owner) или `SYSTEM_ADMIN`. Чтение ограничено tenant-ом и RLS.

## UI / UX
- Раздел **“Ruleset & Versioning”** в админ-панели.
- Таблица версий: версия, статус (Active/Draft), автор, дата, подпись, комментарий, источники отката.
- Просмотр diff: визуальный jsondiff с подсветкой (`added`, `changed`, `removed`), доступен в модалке.
- Кнопки действий: `Activate`, `Rollback`, `Export JSON`, `Copy signature`.
- Фильтры: период, автор, статус (active, draft, archived), глобальные vs tenant.
- Журнал использования отображает, где версия задействована (комплаенс, отчёты, bulk).

## Интеграции
- **Documents:** чеклисты и проверки используют активную версию или заданную в payload.
- **Compliance:** логирует `ruleset_version_id` в актах проверки.
- **Audit Log:** все изменения, активации, откаты и ошибки пишутся в единый аудит.
- **Reporting:** указывает версию в метриках и экспортируемых отчётах.
- **Import / Export:** позволяет переносить версии между tenant с валидацией подписи.
- **Bulk Operations:** фиксирует используемую версию в `document_ruleset_usage`.

## Безопасность
- RLS по `tenant_id`. Глобальные версии доступны только для чтения.
- Подпись вычисляется на сервере, чтобы исключить подмену.
- JSON валидируется схемой (`ruleset.schema.json`) перед сохранением. При ошибке — 422.
- Откат недоступен для версий, созданных ранее заданной политики хранения (retention).
- Лимит на размер ruleset (<= 512 KB).

## Тест-кейсы
- Создание новой версии → версия инкрементируется, предыдущая помечается неактивной, diff сохранён.
- Смена правил с тем же содержимым → создаётся запись с новой подписью, diff пустой, статус “identical”.
- Откат к версии → создаётся новая активная версия с ссылкой `origin_version_id`, предыдущая активная отключена.
- `GET /ruleset/versions` отдаёт только tenant-специфичные версии (глобальные в append only).
- Попытка записи без роли администратора → 403.
- Проверка подписи → повторное вычисление SHA256 совпадает со значением в версии.
