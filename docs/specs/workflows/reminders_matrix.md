# ⏰ Reminders Escalation Matrix

> Дополнение к `docs/specs/workflows/reminders.md`. Описывает SLA, каналы доставки, получателей и правила дедупликации.

---

## 1. Типы шагов и SLA

| Тип шага / документа | T−24 | T−4 | T+0 | T+N | Каналы | Получатели |
|----------------------|------|-----|-----|-----|--------|------------|
| `documents.expiry` (driver) | In-app | Email | Email + Push | Каждые 24ч после просрочки | In-app, Email, Webhook | Owner (recruiter), Supervisor |
| `documents.expiry` (employer) | In-app | Email | Email | Каждые 24ч после просрочки | In-app, Email, Webhook | Client Manager, Administrator |
| `workflow.process_step_due` | In-app | In-app + Email | Email + Webhook | Каждые 24ч | In-app, Email, Webhook | Assigned recruiter, Supervisor |
| `candidate.follow_up` | In-app | — | — | Через 48ч повтор | In-app | Assigned recruiter |
| `service_order.sla` | In-app | Email | Email + Webhook | Каждый рабочий день | In-app, Email, Webhook | Service owner, Administrator |

**Определения**
- `T−24` — за 24 часа до `due_at`.
- `T−4` — за 4 часа до `due_at`.
- `T+0` — в момент просрочки.
- `T+N` — периодическое повторение после просрочки (`N` указывается в колонке).

---

## 2. Локализуемые шаблоны сообщений

Формат шаблона:
```
notifications.<domain>.<event>.<channel>.<fragment>
```

### Переменные
- `{{ user_name }}` — имя получателя.
- `{{ document_name }}` / `{{ step_title }}` — локализованные названия.
- `{{ due_at }}` — формат ISO или локализованный (UI отвечает за форматирование).
- `{{ tenant_name }}`, `{{ company_name }}`, `{{ candidate_name }}`.

Допустимые HTML-теги: `<strong>`, `<em>`, `<a>`, `<br/>`. Остальные экранируются.

---

## 3. Дедупликация и подавление

- При изменении `due_at` старое напоминание помечается `cancelled`, новое создаётся с теми же каналами.
- Если документ закрыт (`status in ['approved','completed','delivered']`) — все активные напоминания снимаются.
- Для повторных напоминаний используется `digest_key = <entity_type>:<entity_id>:<step_code>`; повтор в течение 1 часа не доставляется.
- Повторная доставка `T+N` продолжается до тех пор, пока статус не станет `done` или `cancelled`.
- Единый `schedule_key=document_expiry:<offset>` обеспечивает идемпотентность и подавление дублей при пересчёте SLA.

---

## 4. Каналы доставки

| Канал | Инфраструктура | Заметки |
|-------|----------------|---------|
| In-app | `/api/v1/notifications` | Хранится в `user_notifications`, фолбэк на en |
| Email | SendGrid (prod) / console backend (dev) | Шаблоны локализуются через i18n |
| Webhook | `POST /api/v1/settings/webhooks` | Подпись HMAC, idempotency key |
| Push | Expo (mobile) / browser push (roadmap) | Пока только уведомления документов |

---

## 5. Проверки

- [ ] Тесты покрывают генерацию T−24/T−4/T+0/T+N для документа.
- [ ] При переносе `due_at` создаётся ровно одно активное напоминание.
- [ ] Удаление документа или шага вызывает `status=cancelled`.
- [ ] Отправка webhook содержит `idempotency_key` и подписана секретом.
- [ ] Локализация шаблонов проверена (ключи существуют в `en`, `ru`, `pl`).
