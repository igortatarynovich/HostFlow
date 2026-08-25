# Document Expiry — Workflow Specification

**Status:** canonical (E6 seal)  
**SoT:** Document Hub validity field (`documents.expire_date` / public `expires_at`)  
**Parents:** [Documents Platform E6](../tasks/documents-platform-e6-document-expiry.md) · [Documents Public Contract](../architecture/documents-public-contract.md) · [ADR-009](../architecture/ADR-009-document-hub-platform-layer.md) · [ADR-012](../architecture/ADR-012-activity-notification-operating-layer.md)

Этот документ описывает контроль срока действия **документа как сущности Hub**, а не пайплайн кандидата. Напоминания и задачи живут в Activity & Notification operating layer ([ADR-012](../architecture/ADR-012-activity-notification-operating-layer.md)). Document Hub **публикует** `document.expired` / expiring; он **не** владеет таблицей reminder/task.

---

## Цель

Сделать срок действия свойством Document Hub, которое потребители читают только через `documents.public_contract.v1` / `documents.hub_adapter_v1`. Кандидат (D4) и HR employee (D8) **размещают** поверхность `documents`; они не владеют оценкой срока. `next_action` и смена статуса человека — модульные потребители, не Documents SoT.

---

## Задействованные объекты

- **Document (Hub)** — SoT срока: `expire_date` (public `expires_at`). Оценка: `document_expiry_engine` (`valid` / `expiring_soon` / `expired`; нет даты → документ не участвует).
- **Document Link** — `document_entity_links` (`candidate` / `primary`, `workforce_employee` / `reused_for_hr`). Связь с человеком не является сроком.
- **Catalog events** — уже названы: `document.created` / `linked` / `verified` / `expired`. E6 не минтит новое событие.
- **Activity & Notification (ADR-012)** — reminders / tasks / уведомления. Не таблица Document Hub.
- **Recruitment UOS** (`next_action.py`) — может *потреблять* `document_expired` / `document_expiring_soon`. Это не public contract Documents.

`documents.candidate_id` **снят** (E5). Expiry workflow does not read Candidate FK and does not flip Candidate status as Documents SoT.

---

## Основные правила

- Срок — на Document, не на Link и не на Candidate.
- Публичное чтение: Hub view `expires_at` + `expiry_state` (+ `days_left`) на `GET /api/v1/platform/documents/resolve`.
- Типы с контролем срока задаёт **Hub type catalog** (expiry field / `expiry_rule`) — не локальный список в этом workflow (Architecture Rule 1).
- Документы без даты истечения не участвуют в expiry evaluation.
- Проверка evaluation — Documents-owned (`document_expiry_engine`). Планировщик уведомлений — Activity layer.
- Если документ истёк:
  - Hub evaluation = `expired`;
  - Catalog `document.expired` (уже named) может быть опубликован;
  - Activity layer может создать reminder / notification;
  - **запрещено** считать автосмену статуса кандидата Documents SoT.

---

## События и действия

| Событие | Условие | Действие (владелец) |
|----------|----------|---------------------|
| `document.created` / `updated` | Есть `expire_date` | Hub хранит дату; evaluation доступна на public resolve |
| `document.expired` | `expiry_state = expired` | Catalog event (already named). Activity layer may notify. Hub does not insert a reminder row |
| `document.expiring` | `expiry_state = expiring_soon` | Activity layer may notify. Not a second Documents Adapter |

`document.revalidated` / Candidate pipeline flips remain **module** reactions, not Hub writes.

---

## Уведомления

- Канал, шаблон и дедуп — Activity & Notification (ADR-012), не Document Hub.
- Тема/копия могут упоминать связанного кандидата через Document Link — это consume, не SoT.
- Частота и ACL получателей — Activity layer.

---

## Исключения

- Нет `expire_date` → нет `expiry_state` на public view.
- Продление = новая/обновлённая дата на Document; evaluation пересчитывается. Hub не хранит очередь задач.
- Модуль может не слать уведомления для отклонённых/закрытых карточек — это модульное правило, не Documents SoT.

---

## Метрики

- Количество документов с `expiry_state = expired` (Hub).
- Время реакции и доставка уведомлений — Activity layer.

---

## Invariants (E6)

1. Validity is on the Document, not on a Link.  
2. Modules consume only the public contract / adapter.  
3. No Document Hub reminder / task table.  
4. No `documents.candidate_id` in this workflow.  
5. D4 / D8 stay bound; D3 / D5–D7 / D9 stay unbound.  
6. Documents Foundation stays 🔄.

---

## AI Agent Notes

- Public consume = `documents.hub_adapter_v1` resolve view, not Candidate FK lists.  
- Do not mint `hub_adapter_v2` or a Hub `reminders` table.  
- Do not treat `next_action` as the Documents public contract.  
- Tenant + RLS remain mandatory on every document read.
