# 🛡️ HostFlow RBAC Matrix & Panels

> Официальная матрица ролей, ресурсов и панелей. Используется для backend.guard декораторов, frontend conditional UI и тестов доступа.

---

## 1. Панели и назначение

| Панель | URI-префикс | Роли | Описание |
|--------|-------------|------|----------|
| Platform Control Center | `/api/v1/platform/*` | `superadmin` | Управление лицензиями, white-label, глобальными интеграциями, аудитом |
| Tenant Admin Console | `/api/v1/settings/*` | `administrator` (write), `supervisor` (read-only) | Настройки внутри тенанта: пользователи, ruleset, локализация, импорт CSV, routing |
| Supervisor Dashboard | `/api/v1/supervisor/*`, `/api/v1/leads/*` (read/all) | `administrator`, `supervisor` | Контроль пайплайнов, unmatched leads, SLA напоминаний и документов |
| Recruiter Workspace | `/api/v1/leads/*`, `/api/v1/candidates/*`, `/api/v1/documents/*` | `administrator`, `supervisor`, `recruiter` | Операционная работа с лидами/кандидатами/документами |
| Client Portal | `/api/v1/client/*` | `client_manager` | Доступ компании к своим кандидатам и документам |
| Candidate Portal | `/api/v1/candidate/*` | `candidate` | Личный кабинет кандидата |

> Настройки всегда располагаются в `/api/v1/platform` или `/api/v1/settings`. Рабочие модули не должны содержать конфигурационных эндпоинтов.

---

## 2. Роли и соответствие панелям

| Роль | Панели | Примечания |
|------|--------|------------|
| `superadmin` | Platform Control Center, Tenant Admin Console (impersonation) | Может переключаться между тенантами, видеть все данные |
| `administrator` (`owner`) | Tenant Admin Console, Supervisor Dashboard, Recruiter Workspace | Управляет пользователями, шаблонами, импортом CSV, локализацией |
| `supervisor` | Supervisor Dashboard, Recruiter Workspace | Контроль пайплайнов, отмечает напоминания, видит unmatched лиды, но не меняет глобальные настройки |
| `recruiter` | Recruiter Workspace | CRUD по лидам, кандидатам, документам в пределах доступа |
| `client_manager` | Client Portal | Ограничен своей компанией (`company_id`) |
| `candidate` | Candidate Portal | Только собственные данные |
| `viewer` | Supervisor Dashboard (read-only) | Нет прав на изменения |

---

## 3. Матрица ресурсов (основные сущности)

### 3.1 Документы / Documents

| Действие | superadmin | administrator | supervisor | recruiter | client_manager | candidate |
|----------|------------|---------------|------------|-----------|----------------|-----------|
| `list` | ✅ (impersonation) | ✅ | ✅ | ✅ | ✅ (только свои компании) | ✅ (только свои) |
| `read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `create` | ✅ | ✅ | ⚠️ (может создавать процессные шаги/напоминания) | ✅ | ❌ | ✅ (ограниченные типы, upload) |
| `update` | ✅ | ✅ | ⚠️ (workflow, due_at) | ✅ | ❌ | ⚠️ (только файлы) |
| `delete` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `manage_templates` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

> ⚠️ Supervisor может менять `workflow.steps[*].due_at` и отмечать выполненными, но не может удалять документы.

### 3.2 Лиды / Leads

| Действие | superadmin | administrator | supervisor | recruiter | client_manager |
|----------|------------|---------------|------------|-----------|----------------|
| `list` | ✅ (impersonation) | ✅ | ✅ | ✅ | ❌ |
| `read` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `create` | ✅ | ✅ | ⚠️ (может создавать follow-up задачи) | ✅ | ❌ |
| `update` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `needs_routing` управление | ✅ | ✅ | ❌ | ❌ | ❌ |
| `import_csv` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `webhook_settings` | ✅ | ✅ | ❌ | ❌ | ❌ |

> Распределять лидов, не прошедших маппинг, могут только `administrator` внутри тенанта или `superadmin` от имени тенанта.

> `supervisor` имеет read-only доступ к `/api/v1/settings/leads/**`: может просматривать настройки, credential'ы, маппинг и прогресс import jobs, но не запускать импорт и не изменять конфигурацию.

### 3.3 Напоминания / Reminders

| Действие | superadmin | administrator | supervisor | recruiter | client_manager |
|----------|------------|---------------|------------|-----------|----------------|
| `list` | ✅ (audit) | ✅ | ✅ (весь тенант) | ✅ (свои кандидаты/документы) | ✅ (свои документы) |
| `mark_done` | ✅ | ✅ | ✅ (эскалационные напоминания) | ✅ (свои) | ✅ (свои) |
| `escalate` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `configure_sla` | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 4. Делегирование прав клиента

- Клиент (компания) может назначить дополнительных менеджеров через Client Portal (`POST /api/v1/client/users`).
- Делегированные менеджеры наследуют роль `client_manager` и видят только данные своей компании.
- Делегирование хранится в таблице `company_access` (см. `modules/companies.md`).
- Удаление делегирования немедленно отзывает доступ (audit log обязателен).

---

## 5. Проверки и middleware

- Каждый запрос проходит через `get_current_user` (см. `backend/app/auth/deps.py`), который определяет роль и тенант.
- Middleware `ensure_auth_multitenancy` устанавливает `app.tenant_id` и проверяет, что пользователь имеет доступ к панели, соответствующей пути.
- Для `/api/v1/settings/*` требуется `administrator` или `superadmin`; GET-запросы к `/api/v1/settings/leads/**` доступны также `supervisor` (read-only).
- Для `/api/v1/platform/*` требуется `superadmin`.
- Для `/api/v1/client/*` — `client_manager` и совпадение `company_id`.

---

## 6. Тестовый чек-лист

- [ ] Интеграционные тесты подтверждают, что `recruiter` не может вызвать `/api/v1/settings/*`.
- [ ] Тест на запрет ручного распределения лидов `needs_routing` для `recruiter`/`supervisor`.
- [ ] Тесты документов проверяют, что `client_manager` видит только свои документы.
- [ ] Smoke-тест UI скрывает настройки от рекрутёров.
- [ ] Audit лог фиксирует все эскалации и изменения ролей.
