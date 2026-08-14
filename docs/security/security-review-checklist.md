# Security Review Checklist (PR Gate)

Использовать **для каждого PR**, который затрагивает: API, схему БД, RLS, аутентификацию, документы, экспорт, поиск, webhooks, публичные ссылки, порталы (client/candidate), handoff, автоматизации, уведомления, загрузки файлов.

Копируйте блок ниже в описание PR или прикрепляйте ссылку на этот файл.

---

## Чеклист (обязательно)

### 1. Tenant isolation

- [ ] Фоновые джобы / webhooks открывают сессию через `tenant_enforced_session` или эквивалент (`tenant_rls_enforcement=True` + `bind_tenant_context_to_session`), а не «сырой» `async_session_maker` без bind.
- [ ] Нет путей чтения/записи без установки DB tenant context (включая фоновые задачи, bulk, raw SQL).
- [ ] `tenant_id` / `X-Tenant-Id` с клиента **не** являются единственным источником истины.
- [ ] Добавлены/обновлены **негативные** тесты: чужой tenant → 403/404 без утечки данных.

### 2. RBAC и policy layer

- [ ] Права проверены на **API**, не только в UI.
- [ ] Нет новой логики «`if role == ...`» без использования общего guard / permission service.
- [ ] Скрытые поля (internal notes, payroll, CLASS 3) не попадают в ответы для client/candidate/viewer без явного allowlist.
- [ ] Если меняются trust roles / matrix / invites: соблюдён инвариант **ADR-036** (4 trust-роли; ceilings; `access_context` ⊥ role); job titles = presets; см. `threat-models/rbac-trust-roles.md`.

### 3. Handoff и cross-tenant

- [ ] Если затронут handoff / shared visibility: обновлены policy, audit, экспорт, уведомления; см. `docs/security/security-ssot.md` §5 и `threat-models/handoff.md`.
- [ ] Явно указан **ACCESS CONTEXT** (OWNER / SHARED_READ / SHARED_PROCESSING / TRANSFERRED) в коде или спеке.

### 4. Документы и ссылки

- [ ] Нет новых публичных прямых URL на файлы без подписи и короткого TTL.
- [ ] Генерация signed URL только после проверки права.
- [ ] CLASS 3: аудит + короткий TTL (см. SSOT §2, §7).

### 5. Загрузки файлов

- [ ] Валидация размера, расширения, MIME/signature.
- [ ] Candidate portal: upload token изолирован от session auth (если менялся upload flow).
- [ ] Учтены zip/svg/exe bypass сценарии (см. `threat-models/document-uploads.md`).

### 6. Экспорт

- [ ] Audit: кто / что / сколько строк / когда.
- [ ] Rate limit / batch limit не ослаблены без обоснования.

### 7. Интеграции и webhooks

- [ ] Webhooks: подпись, секреты не в коде; при изменении контракта — заметка о replay/allowlist.
- [ ] Исходящие HTTP из автоматизаций не расширяют SSRF surface без allowlist.

### 8. Аутентификация и сессии

- [ ] Новые публичные endpoint-ы: rate limit / abuse considerations.
- [ ] Cookies/headers не ослабляют `SameSite`/`HttpOnly`/`Secure` без причины.

### 9. Заголовки и конфигурация edge

- [ ] Если меняется способ отдачи статики/API через proxy — проверено соответствие `security-ssot.md` §12.

### 10. Зависимости

- [ ] Нет намеренного downgrade зависимостей с известными critical CVE без mitigation.
- [ ] Если добавлены пакеты — отмечено для сканирования (pip-audit / npm audit).

### 11. Документация

- [ ] Обновлён `docs/security/threat-models/*` при новой attack surface.
- [ ] При смене модели данных — `docs/specs/**` и при необходимости `security-ssot.md`.
- [ ] Acquisition Activity Timeline / `acquisition_activity_events`: см. [`threat-models/acquisition-activity-timeline.md`](threat-models/acquisition-activity-timeline.md) (append-only, RLS, tenant-scoped idempotency, no Ops FKs).
- [ ] Acquisition Optimization Signals (Stage 5): см. [`threat-models/acquisition-optimization-signals.md`](threat-models/acquisition-optimization-signals.md) (read-only, company-scope, no Activity on GET, no auto-pause).
- [ ] Marketing Sources (C-3/C-4): см. [`threat-models/acquisition-marketing-sources.md`](threat-models/acquisition-marketing-sources.md) (C-3 inventory GET; C-4 sample/preview tenant isolation, masked PII, preview no production entity create).
- [ ] Source Diagnostics (PR1–PR9): см. [`threat-models/acquisition-source-diagnostics.md`](threat-models/acquisition-source-diagnostics.md) (read-only Lead + Activity compose; filters; duplicate; Mapping Health; drift alerts/summary; export; Replay via Leads process; SPA-only drift notify; tenant scope; no Diagnostics write on GET).
- [ ] Communication Campaign Orchestrator (C2.3): см. [`threat-models/communication-campaign-orchestrator.md`](threat-models/communication-campaign-orchestrator.md) (Intent-only, tenant scope, no provider/Thread, distinct from Acquisition campaigns).
- [ ] Forms Platform (C2 identity + C3 Builder + C4 Runtime + C5 Execution + C6 Optimization): см. [`threat-models/forms-platform.md`](threat-models/forms-platform.md) (frozen publication identity; FormDefinition ↔ Draft only; Runtime Model read-only; Execution validates Runtime Model only; production apply-submit resolve→serve→execute; Shared Intake write path; no Builder↔Runtime/Execution import; tenant resolve; submit pin; fail-closed backfill).

---

## Классификация PR по уровню review

| Уровень | Примеры | Кто смотрит |
|---------|---------|-------------|
| **S0** | Новый публичный route, document download, export, webhooks, handoff | Обязательно security-minded reviewer |
| **S1** | Изменение RBAC, RLS, JWT claims, portal | Backend lead + второй reviewer |
| **S2** | Чистый internal UI без API | Стандартный review; security чеклист по релевантности |

---

## Mini-review: high-risk surfaces (обязательно при затрагивании)

Если PR затрагивает **любую** из колонок ниже — заполните соответствующую строку (даже если ответ «нет изменений в поведении»).

| Surface | Tenant scope | RBAC | Telemetry (`emit_security_event_v1` / helpers) | Raw payload leakage | Retrieval governance | Document / export logging |
|---------|--------------|------|--------------------------------------------------|---------------------|----------------------|---------------------------|
| **AI / LLM** | | | | | | |
| **Search (global / full-text)** | | | | | | |
| **Exports** | | | | | N/A | |
| **Portals (client / candidate)** | | | | | N/A | |
| **Automations** | | | | | N/A | |
| **Integrations / webhooks** | | | | | N/A | |
| **Analytics / reporting** | | | | | N/A | |

**Проверять кратко:** tenant scope, RBAC, telemetry, утечки raw payload, retrieval governance (если есть RAG/embeddings), document/export audit.

---

## Search / AI feature entry (merge criterion)

**Ни одна** фича из списка ниже **не merge’ится** без явного подтверждения в PR (чекбоксы или ссылка на спеку с тем же содержанием):

- AI assistant / copilot-подобные сценарии
- Global search (не scoped tenant)
- Embeddings / vector store
- Retrieval layer / RAG
- Semantic search

**Обязательно до merge:**

- [ ] Доступ к данным только через **retrieval helper** (или эквивалент из SSOT), без ad-hoc SQL/ORM в «умном» слое.
- [ ] **Tenant scope** enforced end-to-end (включая фоновые джобы и кэш ключей).
- [ ] **RBAC scope** совпадает с тем, что видит пользователь в UI/API.
- [ ] **Audit event** (`emit_security_event_v1` + правильный `event_type` / `source`) на чувствительных операциях.
- [ ] **Нет** логирования raw prompt / полного retrieval payload в application logs или `extra` security events (только хэши/length/redacted summary по политике).

---

## Incident Response runbooks

### A. Подозрение на утечку данных между тенантами или наружу

1. Зафиксировать время обнаружения и scope (tenant, тип данных).  
2. Отключить или сократить TTL **публичных** ссылок в затронутом модуле (если применимо).  
3. Принудительно инвалидировать сессии/токены при утечке секрета или JWT ключа.  
4. Ротировать скомпрометированные секреты (webhook, OAuth, storage signing key).  
5. Включить read-only / feature kill-switch для модуля до разбора.  
6. Post-mortem: RCA, тикеты на тесты и исправления.

### B. Компрометация учётных данных

1. Блокировка учётки, принудительный logout всех сессий пользователя.  
2. Аудит последних 24–72ч действий (логины, экспорты, скачивания).  
3. Уведомление владельца тенанта по каналу из процесса.

### C. Malware или опасный файл в storage

1. Пометить объект как quarantined; запретить повторную выдачу URL.  
2. Запустить ретро-скан по bucket/prefix за период.  
3. Аудит: кто скачивал/открывал файл до карантина.

---

## Связанные документы

- `docs/security/security-ssot.md`
- `docs/security/threat-models/README.md`
- `docs/specs/architecture/rbac_matrix.md`
- `.github/workflows/security-gates.yml` — автоматические проверки (pip-audit, bandit, npm audit, Trivy, threat-model gate, SQL f-string scan)
