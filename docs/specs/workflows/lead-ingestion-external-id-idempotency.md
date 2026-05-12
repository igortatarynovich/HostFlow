# Lead ingestion: `external_id` и идемпотентность (v1.1)

**Цель:** зафиксировать, как HostFlow предотвращает **два Lead** и **два Candidate** при повторной доставке одного и того же события (webhook / Meta / generic inbound), без обязательной новой миграции.

**Связанные документы:** [candidate-creation-entrypoints-audit.md](candidate-creation-entrypoints-audit.md), [lead-conversion-contract.md](lead-conversion-contract.md).

---

## 1. Где хранится `external_id`

- Колонка **`leads.external_id`** (`String(128)`, nullable) — см. миграция `202601010001_meta_webhook_verify_token.py`.
- При создании лида в пайплайне задаётся из нормализованного payload (например Meta `raw_lead_id`) — см. `process_normalized_lead` / `reprocess_stored_lead_payload` (`external_id` параметр → `normalized_external_id`).

---

## 2. Поиск существующего лида

- **`crud.get_lead_by_external_id(db, tenant_id=..., source=..., external_id=...)`** — `SELECT ... WHERE tenant_id AND source AND external_id`, порядок `created_at DESC`, лимит 1.
- В **`process_normalized_lead`** приоритет: `target_lead_id` (reprocess) → иначе lookup по `(tenant_id, source, external_id)` если `external_id` не пустой.

Итог: повторная доставка с **тем же** `tenant_id + source + external_id` должна попадать в **ту же** строку `leads`, если она уже закоммичена до второго запроса.

---

## 3. Уникальность на уровне БД

- Частичный **уникальный** индекс PostgreSQL: **`uq_leads_tenant_source_external_id`** на `(tenant_id, source, external_id)` **WHERE `external_id IS NOT NULL`** (та же миграция `202601010001`).
- Следствие: второй `INSERT` лида с тем же ключом получает **`IntegrityError`**, а не «тихий» дубликат.

**Ограничения:**

- При **`external_id IS NULL`** уникальность по этому индексу **не** действует — возможны несколько lead-строк и несколько конверсий (gap для источников без стабильного внешнего id).
- Ключ включает **`source`**: один и тот же внешний id при **`meta`** и **`webhook`** — **разные** строки (by design); интеграции должны стабилизировать `source` + `external_id`.
- Индекс с `postgresql_where` относится к PostgreSQL; окружения с другим диалектом могут вести себя иначе.

---

## 4. Поведение пайплайна (v1.1)

1. **Lookup** до вставки — как в §2.
2. **Гонка двух параллельных запросов:** оба не находят lead → оба пытаются `create_lead` → второй получает `IntegrityError` на flush. Обработка: **`begin_nested` + перехват `IntegrityError` + повторный `get_lead_by_external_id`** и продолжение с обновлением payload (см. `service/_processing.py`).
3. **Conversion wrapper** (`lead_candidate_conversion.py`): если у лида уже есть **`candidate_id`** — не выполнять второй `INSERT` в `candidates`, audit с `idempotent_replay=True`.

Состояние **`assignment_state` в audit `candidate_created`** — на момент INSERT dossier (до последующих `record_candidate_reassignment`); см. комментарий в контракте.

---

## 5. Что сознательно не сделано

- Нет второго кандидата по «склейке» разных `lead.id` с одним `external_id` в обход БД — при нормальной БД это недостижимо при непустом `external_id`.
- Public intake / Telegram — по-прежнему отдельные пути создания `Candidate` (см. аудит entry points).
