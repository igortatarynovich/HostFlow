# 📄 Documents Workflow Contract

> Дополнение к `docs/specs/modules/documents.md`. Фиксирует обязательные поля workflow, правила статусов, напоминания и права редактирования.

---

## 1. JSON-схема workflow

```json
{
  "type": "object",
  "required": ["steps", "current_step"],
  "properties": {
    "current_step": {
      "type": ["string", "null"],
      "description": "code текущего шага; null если процесс завершён"
    },
    "auto_status": {
      "type": ["string", "null"],
      "description": "системный статус, рассчитанный на основе шагов"
    },
    "notes": {
      "type": ["string", "null"],
      "maxLength": 2000
    },
    "steps": {
      "type": "array",
      "items": { "$ref": "#/$defs/step" },
      "minItems": 1
    }
  },
  "$defs": {
    "step": {
      "type": "object",
      "required": ["code", "title"],
      "properties": {
        "id": { "type": "string", "format": "uuid" },
        "code": { "type": "string", "pattern": "^[a-z0-9_\\.]+$" },
        "title": { "type": "string", "maxLength": 120 },
        "due_at": { "type": ["string", "null"], "format": "date-time" },
        "due_in_hours": { "type": ["integer", "null"], "minimum": 1 },
        "ordered_at": { "type": ["string", "null"], "format": "date-time" },
        "completed_at": { "type": ["string", "null"], "format": "date-time" },
        "actor_id": { "type": ["string", "null"], "format": "uuid" },
        "reminder_id": { "type": ["string", "null"], "format": "uuid" },
        "notes": { "type": ["string", "null"], "maxLength": 1000 },
        "attachments": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "file_id"],
            "properties": {
              "id": { "type": "string", "format": "uuid" },
              "file_id": { "type": "string", "format": "uuid" },
              "added_at": { "type": "string", "format": "date-time" }
            }
          }
        }
      }
    }
  }
}
```

---

## 2. Таблица auto-status (`compute_auto_status`)

| Выполненные шаги (комбинация) | auto_status | Применимо к |
|-------------------------------|-------------|-------------|
| Нет завершённых шагов | `requested` | Любой процесс |
| `ordered` | `in_progress` | work_permit, visa, residence_card |
| `ordered` + `submitted` | `submitted` | work_permit, visa |
| `approved` | `approved` | work_permit, visa, residence_card |
| `delivered` | `delivered` | work_permit, visa, residence_card |
| Любой шаг с `completed_at` и `due_at < now()` | `overdue` | Все процессы |
| All steps `completed_at` заполнены | `completed` | Все процессы |

> Алгоритм: идём по цепочке шагов и выбираем максимальный статус. Если есть просроченные незавершённые шаги — статус `overdue`, даже если предыдущие завершены.

---

## 3. Правила напоминаний

- При создании шага с `due_at` или `due_in_hours` автоматически создаётся напоминание (`reminder.type = process_step_due`).
- Напоминание активирует цепочку эскалаций из `docs/specs/workflows/reminders_matrix.md`.
- При пометке шага `completed_at` напоминание снимается (статус `cancelled`).
- Изменение `due_at` → напоминание переcоздаётся, предыдущая запись помечается `cancelled` (audit).
- Для шагов без `due_at` напоминания не создаются.

---

## 4. Политики редактирования

| Поле | Кто может менять | Ограничения |
|------|------------------|-------------|
| `workflow.steps[*].due_at` | `administrator`, `supervisor` | Лог ≥ `now`, audit запись обязательна |
| `workflow.steps[*].ordered_at` | `administrator`, `recruiter` | Нельзя выставлять в будущем |
| `workflow.steps[*].completed_at` | `administrator`, `supervisor`, `recruiter` (если assigned) | Не позже `now`, требует комментария |
| `workflow.steps[*].notes` | `administrator`, `supervisor`, `recruiter` | Макс 1000 символов |
| `workflow.current_step` | Считается автоматически, изменение вручную запрещено | |
| `workflow.auto_status` | ТОЛЬКО системой (`compute_auto_status`) | Запрещено редактировать вручную |

---

## 5. Интеграция с UI

- UI обязан визуализировать таймлайн шагов, текущий статус и SLA.
- Редактирование `due_at` доступно только supervisor/admin (UI проверяет роль).
- Пользователю показываются локализованные названия шагов (`i18n` ключи `documents.workflow.step.<code>`).
- В случае отсутствия шаблона документов, UI предлагает создать документ вручную из каталога `doc_type`.

---

## 6. Тестовый чек-лист

- [ ] POST `/api/v1/documents` валидирует `workflow.steps[]` по схеме.
- [ ] PATCH `/api/v1/documents/{id}` пересчитывает `auto_status` и напоминания.
- [ ] Изменение `due_at` создаёт единственное активное напоминание.
- [ ] Нельзя записать `completed_at` в будущем.
- [ ] UI показывает корректный фолбэк переводов (`pl` → `en`).
