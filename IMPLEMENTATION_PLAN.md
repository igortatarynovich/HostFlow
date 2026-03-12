# HostFlow: План реализации RODO + Handoff + Processor + Контактные попытки + Нормализация

> Документ для работы по реализации. Содержит контекст решений, ТЗ и поэтапный план. Используйте для прогресса и заметок.

---

## 1. Контекст и принятые решения

### Источник требований
- ТЗ: `/opt/HostFlow/upgrade.md`

### Ключевые архитектурные решения

| Тема | Решение | Комментарий |
|------|---------|-------------|
| **Handoff** | Кастомная функция per клиент (флаг в `tenant_links`) | Продукт гибче: включаем только для выбранных клиентов |
| **Tenant модель** | Два типа: `agency`, `employer`. Связи через `tenant_links` | Агентства дают доступ клиентам; транспортные компании могут принимать поток от нескольких агентств |
| **Контактные попытки** | Фича per карточка/профиль; лимит и пост-действие настраиваемы | Опция: включать/выключать, кол-во попыток, auto_reject или смена стейджа |
| **Этапы и права** | Стейджи не влияют на права; ответственность — только handoff + ACL | Вариант A: не трогаем аналитику по стейджам |
| **Возврат handoff** | Меняем только ACL; связи с вакансией/компанией не трогаем | |
| **Новые роли** | Только `client_processor` | Остальные роли — как есть |
| **Один handoff** | Кандидат может быть передан только одному клиенту в момент времени | |

### Бизнес-модель (влияет на архитектуру)
- **Агентства** — платная подписка; могут подключать клиентов (влияет на стоимость)
- **Транспортные компании** — прямая подписка; работают со своими кандидатами и/или принимают поток от агентств
- У клиента может быть несколько агентств; handoff — опция на уровне tenant_link

---

## 2. Фазы реализации

### Фаза 0. Инфраструктура tenants & links

**Цель:** Разнести agency/employer и подготовить handoff как опцию.

**Задачи:**
- [x] Миграция: `tenants.tenant_type` — уже есть (type: agency|company|platform), `client_portal_enabled`
- [x] Миграция: `tenant_links` (agency_tenant_id, client_company_id, client_tenant_id, status, features_json)
- [x] Seed/миграция текущих связок «агентство ↔ компания» в `tenant_links`
- [x] ACL: не меняем в Фазе 0 (будет в Фазе 4 при handoff)
- [x] API: `GET/PATCH /tenants/{id}/links` — управление handoff_enabled, contact_policy
- [x] По умолчанию `handoff_enabled = false`
- [x] Обновить [multi_tenant_model.md](./docs/specs/architecture/multi_tenant_model.md)

**Deliverables:** Схемы БД, миграции, сервисы tenant_links, тесты ACL.

**Заметки:**
<!-- добавьте свои заметки -->

---

### Фаза 1. Единый аудит-лог

**Цель:** Готовность событийной модели для всех остальных фич.

**Задачи:**
- [x] Использовать ActivityLog (action=event_type, target_type=entity_type, target_id=entity_id)
- [x] Enum: `AuditEventType`, `AuditEntityType` (handoff_*, rodo_*, contact_attempt_*, processor_change, rejected_no_contact)
- [x] Сервис `log_audit_event()` в `backend/app/services/audit.py`
- [x] Unit-тесты в `tests/test_audit_events.py`
- [x] Baseline: события будут проставлены в Фазах 2–5 при реализации RODO, handoff, contact_attempts

**Deliverables:** Обновлённая модель, сервис, тесты.

**Заметки:**
<!-- -->

---

### Фаза 2. Legal documents + RODO (форма и FB-лиды)

**Цель:** Юридическая база и автоматизация RODO.

**Задачи:**
- [x] Таблица `legal_documents`, `rodo_notifications` (миграция 202608020001)
- [x] API: POST /legal-documents (create), GET /legal-documents/active
- [x] Публичная анкета: consent payload с source=public_form, rodo_version_id, privacy_version_id
- [x] rodo_notifications + сервис send_rodo_email (webhook notify)
- [x] UI блок RODO в CandidateCard: кнопка «Wyślij informację RODO», статус sent
- [x] audit: rodo_sent
- [ ] Чекбокс/ссылки на active legal docs в форме — нужна интеграция фронта (GET /active + X-Tenant-Id)

**Deliverables:** Модели legal_documents, rodo_notifications, обновлённые формы, UI, шаблон email.

**Заметки:**
<!-- -->

---

### Фаза 3. Контактные попытки (фича-профиль)

**Цель:** Настраиваемый процесс попыток связи.

**Задачи:**
- [x] Таблица `contact_attempts`, `final_no_contact_notifications`
- [x] tenant_link.features_json.contact_policy: enabled, max_attempts, post_action, stage_code
- [x] API: GET/POST /candidates/{id}/contact-attempts, GET .../policy
- [x] UI: модалка «Zarejestruj próbę kontaktu», список попыток в карточке
- [x] Бизнес-логика: attempt_number, запрет превышения, audit
- [x] Авто-reject после N no_contact: final message, status=rejected, status_reason

**Deliverables:** Модель, сервисы, UI.

**Заметки:**
<!-- -->

---

### Фаза 4. Handoff (кастомная функция)

**Цель:** Передача ответственности для выбранных клиентов.

**Задачи:**
- [x] Модель `candidate_handoffs`, миграция 202608040001
- [x] API: create, accept, reject, return, list pending, available-clients
- [x] Сервис handoff + проверка handoff_enabled
- [x] UI: кнопка «Przekaż do klienta», модалка выбора клиента
- [ ] UI клиента: экран «Do procesowania» (отдельная страница)
- [ ] ACL переключение при accepted/returned (Phase 5)
- [ ] Уведомления (Phase 6)
- [x] audit: handoff_requested, accepted, rejected, returned

**Deliverables:** Модель, API, UI agency.

**Заметки:**
<!-- -->

---

### Фаза 5. Processor и участники

**Цель:** Явное назначение processor.

**Задачи:**
- [x] Роль `client_processor` в Role enum
- [x] processor = handoff.assigned_to_user_id (Variant B)
- [x] PATCH /handoffs/{id}/processor + audit processor_changed
- [x] UI: processor в карточке; страница «Do procesowania» (Accept/Reject)
- [ ] candidate_participants — отложено (assigned_to достаточно для 1.0)

**Deliverables:** Роль, API, UI.

**Заметки:**
<!-- -->

---

### Фаза 6. Уведомления

**Цель:** Событийные уведомления по ТЗ.

**Задачи:**
- [x] handoff_requested → assigned_to или UserCompanyAccess (in-app + webhook)
- [x] handoff_accepted, handoff_rejected → manager, requested_by (in-app + webhook)
- [x] handoff_returned → manager, requested_by (in-app + webhook)
- [ ] rodo_sent_failed — требуется callback от email-сервиса
- [ ] Шаблоны email — webhook передаёт событие, внешний сервис рендерит

**Deliverables:** Event handlers (emit_event), send_webhook для email.

**Заметки:**
<!-- -->

---

### Фаза 6b. Email (SMTP) — настройка через UI

**Цель:** Клиент с подпиской может сам настроить почту и wysyłać maile (RODO, powiadomienia).

**Задачи:**
- [x] Миграция `tenant_email_config`, model `TenantEmailConfig`
- [x] Сервис `tenant_email.py`: SMTP send, encrypt password, `send_email_for_tenant`
- [x] API: GET/PUT /settings/email, POST /settings/email/test
- [x] RODO + final_no_contact → `send_email_for_tenant` (SMTP jeśli skonfigurowany)
- [x] UI: Ustawienia → Poczta (SMTP), formularz, test

**Deliverables:** Działa z Google Workspace (smtp.gmail.com:587, App Password).

---

### Фаза 6c. Systemowa poczta (info@hostflow.cc)

**Цель:** Systemowe maile (reset hasła, zaproszenia) z info@hostflow.cc.

**Задачи:**
- [x] Env: SYSTEM_SMTP_HOST, SYSTEM_SMTP_* , FRONTEND_URL
- [x] send_system_email() — SMTP z env lub webhook fallback
- [x] Password reset → wysyła temp hasło na email użytkownika
- [x] Invite → wysyła link/token na email zapraszanego

**Deliverables:** .env.example, users.reset_user_password, admin.create_invite.

---

### Фаза 7. Нормализация данных (латиница)

**Цель:** Хранение оригинала, отображение латиницей.

**Задачи:**
- [x] Справочник `countries` (ISO2, name_pl, name_en)
- [x] Поля first_name_latin, last_name_latin; city_latin, address_latin (в personal_data)
- [x] Сервис транслитерации (кириллица → латиница)
- [x] Миграция + backfill существующих
- [x] UI: подсказка при кириллице; Do procesowania показывает латиницу

**Deliverables:** countries, transliterate, normalization, schema, backfill.

**Заметки:**
<!-- -->

---

### Фаза 8. Массовые операции и UX-полировка

**Цель:** Удобство для агентств и клиентов.

**Задачи:**
- [x] Массовая передача кандидатов (bulk handoff)
- [x] Фильтры/виджеты по handoff, попыткам, processor
- [x] Настройки UI для включения/выключения handoff и contact_policy
- [ ] UX-полировка: состояния кнопок, предупреждения

**Deliverables:** UI доработки, инструкции.

**Заметки:**
<!-- -->

---

### Фаза 9. Миграции и релиз

**Цель:** Плавный rollout.

**Задачи:**
- [ ] Скрипты автосоздания tenant_links для текущих клиентов

### Создание tenant_link для employer tenant (Citronex и др.)

Чтобы клиент (employer tenant) видел handoffs в Do procesowania:

1. Создать tenant_link: `POST /tenants/{agency_tenant_id}/links`
   ```json
   {"client_tenant_id": "UUID_ТЕНАНТА_ЦИТРОНЕКС", "handoff_enabled": true}
   ```
2. При передаче кандидата выбирать этот клиент (tenant) в модалке handoff.
3. Пользователи Citronex зайдут в Do procesowania и увидят очередь по client_tenant_id.
- [ ] Rollout: включать фичи по флагам, пилот на 1–2 клиентах
- [ ] Документация для агентств/клиентов
- [ ] Мониторинг: дашборд по audit events, метрики

**Deliverables:** Миграционные скрипты, rollout чек-лист, документация.

**Заметки:**
<!-- -->

---

## 3. Справочник сущностей (новые/изменённые)

| Сущность | Описание | Фаза |
|----------|----------|------|
| tenant_links | agency ↔ client, handoff_enabled, contact_policy | 0 |
| audit_events / расширение ActivityLog | Единый лог событий | 1 |
| legal_documents | RODO / privacy policy, версии | 2 |
| rodo_notifications | Отправки RODO (email/SMS), immutable | 2 |
| contact_attempts | Попытки контакта, immutable | 3 |
| final_no_contact_notifications | Финальное сообщение при auto_reject | 3 |
| candidate_handoffs | Передача кандидата клиенту | 4 |
| candidate_participants | manager, processor | 5 |
| countries | Справочник стран ISO | 7 |

---

## 4. Зависимости фаз

```
0 (tenants/links) ─┬─► 1 (audit)
                   ├─► 4 (handoff) ─► 5 (processor) ─► 6 (notifications)
                   ├─► 2 (RODO)
                   ├─► 3 (contact attempts)
                   └─► 7 (normalization)

8 (UX) — после 4, 5
9 (release) — после всех
```

---

## 5. Прогресс

| Фаза | Статус | Дата начала | Дата завершения |
|------|--------|-------------|-----------------|
| 0 | ✅ завершена | | |
| 1 | ✅ завершена | | |
| 2 | ✅ завершена | | |
| 3 | ⬜ не начата | | |
| 4 | ✅ завершена | | |
| 5 | ✅ завершена | | |
| 6 | ✅ завершена | | |
| 7 | ⬜ не начата | | |
| 8 | ⬜ не начата | | |
| 9 | ⬜ не начата | | |

---

## 6. Связь с другими документами

| Документ | Связь с планом |
|----------|----------------|
| [upgrade.md](./upgrade.md) | Источник требований (ТЗ) |
| [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) | Общий технический roadmap: RLS, миграции, Documents, Invoicing. Фаза 0 пересекается с tenant/RLS аудитом. При конфликте приоритет — upgrade.md. |
| [docs/specs/architecture/multi_tenant_model.md](./docs/specs/architecture/multi_tenant_model.md) | Текущая модель tenant. **Обновить в Фазе 0** под tenant_links и tenant_type. |
| [docs/analysis/candidate_intake_improvement_plan.md](./docs/analysis/candidate_intake_improvement_plan.md) | План улучшения анкеты. Фаза 2 (RODO checkbox) затрагивает публичную форму — учесть при доработке. |
| [docs/specs/public_intake_new_specification.md](./docs/specs/public_intake_new_specification.md) | Спецификация анкеты. Фаза 2: добавить RODO checkbox и логирование согласия. |
| [CANDIDATE_PORTAL_IMPROVEMENTS.md](./CANDIDATE_PORTAL_IMPROVEMENTS.md) | Улучшения Candidate Portal. Не противоречит; при реализации Фазы 2 — учесть. |
| [docs/scanner/](./docs/scanner/) | Документация сканера (оверлей, отладка, обработка). Не связана с upgrade. |
| [hostflow-frontend/INTake-CHECKLIST.md](./hostflow-frontend/INTake-CHECKLIST.md) | Чеклист QA анкеты. Использовать при тестировании Фазы 2. |

---

## 7. Быстрые ссылки

- [ТЗ upgrade.md](./upgrade.md)
- [EXECUTION_PLAN.md](./EXECUTION_PLAN.md) — общий технический план
- [docs/specs/architecture/multi_tenant_model.md](./docs/specs/architecture/multi_tenant_model.md)
- [docs/scanner/debugging_guide.md](./docs/scanner/debugging_guide.md) — отладка сканера
