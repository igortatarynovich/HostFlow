


# HostFlow: Recruiter Auto-Assignment Logic

> Статус: ✅ реализовано (назначение рекрутёра при создании кандидата, endpoint `/api/v1/recruiters/assign`).

## Цель
Автоматически назначать рекрутера новому кандидату (из лида, импорта или ручного создания) в зависимости от вакансии, загрузки и правил компании.  
Система уже полностью переведена на PostgreSQL.

---

## 1. Основной принцип
Каждый кандидат должен иметь **назначенного рекрутера (`recruiter_id`)** сразу при создании.  
Назначение выполняется на основе:
1. Привязанной вакансии (`vacancy_id`)
2. Таблицы ответственных за вакансию (`vacancy_recruiters`)
3. Текущей загрузки рекрутёров
4. Фолбэков (supervisor / admin)

---

## 2. Структура данных

### vacancy_recruiters
```sql
create table if not exists vacancy_recruiters (
  vacancy_id uuid not null references vacancies(id) on delete cascade,
  user_id uuid not null references users(id) on delete restrict,
  weight int not null default 1,
  is_active boolean not null default true,
  primary key (vacancy_id, user_id)
);
```

### candidates (расширение)
```sql
alter table candidates
  add column if not exists recruiter_id uuid references users(id) on delete set null;
```

---

## 3. Алгоритм назначения

### Псевдокод:
```python
def assign_recruiter(vacancy_id: UUID) -> UUID:
    pool = get_active_recruiters(vacancy_id)
    if not pool:
        return get_supervisor_or_admin(vacancy_id)

    # получить загрузку
    loads = {r.id: count_active_candidates(r.id) for r in pool}

    # вычислить рейтинг (учитывая вес и загрузку)
    scores = {rid: pool[rid].weight / max(1, loads[rid]) for rid in loads}

    # выбрать рекрутера с максимальным score
    return max(scores, key=scores.get)
```

### Детали:
- **count_active_candidates**: считает кандидатов с активными статусами (не «Отклонён», не «Закрыт»).
- Если несколько с одинаковым score → round-robin.
- Если все неактивны → берём `vacancy.owner_id`.
- Если нет никого → фолбэк на `supervisor`.

---

## 4. Логирование и аудит
При каждом назначении создаётся запись:
```json
{
  "candidate_id": "...",
  "vacancy_id": "...",
  "recruiter_id": "...",
  "strategy": "least_load",
  "created_at": "2025-10-26T10:00:00Z"
}
```

Эта запись добавляется в `audit_log` с типом `candidate_assigned`.

---

## 5. API
### Внутренний сервис
`POST /api/v1/recruiters/assign`
```json
{
  "vacancy_id": "uuid"
}
```

Ответ:
```json
{
  "recruiter_id": "uuid",
  "strategy": "least_load"
}
```

Используется внутри пайплайна создания кандидата (Meta Leads → Candidates).

---

## 6. Настройки
В будущем можно добавить стратегию в `vacancies.settings`:
```json
{
  "assignment_strategy": "least_load" | "round_robin" | "owner_only"
}
```

---

## 7. Тесты
- ✅ Один активный рекрутер → назначается он.
- ✅ Несколько — баланс по загрузке.
- ✅ Закрытая вакансия → фолбэк на supervisor.
- ✅ Вакансия без рекрутёров → фолбэк на admin.
- ✅ Проверка, что назначение логируется.

---
