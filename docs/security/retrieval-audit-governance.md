# Search / analytics / AI retrieval — audit governance

**Статус:** нормативный контракт (Phase «retrieval audit»). Helper `retrieval_events.py` + **первый call site** `GET /api/v1/search` (`search.retrieval.completed`). Остальные search/AI surfaces — отдельными PR; **не** смешивать с массовым подключением AI или изменением поведения поиска в одном changeset.

**Аудитория:** platform, backend, security champion, владельцы search / AI features.

---

## Почему это отдельный high-risk слой

Search, аналитика и сбор контекста для AI — **потенциальный bypass layer** поверх tenant isolation и RBAC: один широкий retrieval или «удобный» глобальный индекс сводят на нет RLS, если policy не повторяется на границе retrieval.

Инвариант: **любой retrieval** (поиск по сущностям, подбор чанков для prompt, analytics drill-down, который материализует «сырые» строки) обязан быть одновременно:

1. **Tenant-scoped** — нет implicit global search по всем tenant’ам без явного platform-only режима с отдельным audit и rate limit (см. [`runtime-roadmap.md`](./runtime-roadmap.md), Phase 6).
2. **RBAC-scoped** — тот же policy layer, что и у HTTP API; нельзя «обойти» роль через retrieval helper.
3. **Audit-scoped** — фиксируются попытки и результаты (**requested / completed / denied**), без утечки CLASS 3 в логах.

**AI context builder** не имеет права обходить policy layer: сбор контекста = те же проверки scope, что и у чтения тех же сущностей через API.

---

## Что запрещено логировать (security events и смежные «отладочные» логи)

| Категория | Запрет |
|-----------|--------|
| Prompt / instructions | raw system prompt, user prompt, full message list |
| Query | сырая поисковая строка, полный SQL / FTS query text |
| Context | сырой assembled context, document text, чанки |
| Embeddings | векторы, embedding payloads, serialized floats |
| Обход канала | произвольный `logger.*` с query/prompt/context рядом с секретными полями — см. CI в [`security-events-governance.md`](./security-events-governance.md) |

Разрешены только **таксономические** поля в `extra` после allowlist + redaction (см. `RETRIEVAL_EVENT_EXTRA_ALLOWLIST` в `retrieval_events.py`): тип retrieval, scope, **счётчики** (returned / filtered / denied), policy scope, флаги, **короткий** machine-oriented `reason`, без сырого текста запроса.

---

## Семантика результатов

События должны позволять различать (для будущих детекторов и IR):

* **empty** — разрешено, policy применён, ответ пустой (например `returned_count=0`, отдельно от denied);
* **filtered** — часть кандидатов/документов отфильтрована политикой (`filtered_count` > 0 при `returned_count` ≥ 0);
* **denied** — отказ до или во время retrieval (`search.retrieval.denied` / `ai.retrieval.denied`, `result=denied`, `reason`).

Точная кодировка empty vs filtered — в полях `returned_count`, `filtered_count`, `denied_count` и `result`; не дублировать сырой payload ответа.

---

## События (taxonomy v1, минимум)

| Prefix | `event_type` | Назначение |
|--------|----------------|------------|
| `search.` | `search.retrieval.requested` | Запрос retrieval (поиск) зафиксирован |
| `search.` | `search.retrieval.completed` | Успешное завершение (с метриками счётчиков) |
| `search.` | `search.retrieval.denied` | Отказ (RBAC / tenant / rate / invalid scope) |
| `ai.` | `ai.retrieval.requested` | Запрос на сбор контекста для модели |
| `ai.` | `ai.retrieval.completed` | Контекст собран в рамках policy (без сырого текста в логе) |
| `ai.` | `ai.retrieval.denied` | Отказ до выдачи контекста |

**Analytics** с явным retrieval-слоем (не агрегаты из БД, а именно «поиск/подбор строк») — маппинг на `search.*` или отдельный префикс только после отдельного taxonomy PR. Пока нет слоя — не эмитить «для галочки».

---

## Producer contract

* Только **`emit_security_event_v1`** или **`emit_retrieval_security_event_v1`** из `backend/app/security/retrieval_events.py`.
* Новые `event_type` — отдельный PR в `event_taxonomy.py` + тесты `validate_event_type`.
* Нельзя implicit **global** search: в `extra` фиксируются `retrieval_scope` / `policy_scope` (короткие коды), не сырой query.

Изменения этого документа — через review (platform + security), как и для [`security-events-governance.md`](./security-events-governance.md).
