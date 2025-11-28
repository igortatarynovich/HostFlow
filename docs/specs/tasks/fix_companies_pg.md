


# 🧩 ТЗ: Починка модуля **«Компании»** после перехода на PostgreSQL

## 📍 Контекст

- **Весь проект HostFlow полностью переведён на PostgreSQL 16** (контейнер `hostflow-pg`).
- Все Alembic-миграции применяются корректно, схема актуальна.
- Модуль **Companies** на фронтенде (`/src/pages/Companies.tsx`) теперь открывает **полную карточку** при создании, аналогично модулю кандидатов.
- Бэкенд — FastAPI + SQLAlchemy (`backend/app/api/v1/companies.py`).
- Проблема: данные из новых секций (legal, billing, operations, compliance, portal, integrations и т.д.) **не сохраняются**.
- Дополнительно: необходимо **проверить все связи между модулями** — компании ↔ вакансии ↔ кандидаты, чтобы данные и фильтры работали в обе стороны согласно актуальной документации (`/docs/specs/modules/`).

---

## 🎯 Цель

1. Обеспечить **полное сохранение и загрузку** данных компании, включая все секции `extra` и `contacts`.
2. Обеспечить корректную работу API `/companies` в связке с модулями **Vacancies** и **Candidates**.
3. Проверить все вызовы, которые используют `company_id`, `vacancy_id` и `candidate_id` — ссылки, фильтры, карточки, списки.
4. Гарантировать 100% соответствие текущей документации и спецификации HostFlow.

---

## 📦 Что должно работать

1. **POST /api/v1/companies/**
   - Создаёт черновую компанию `{ "name": "Без названия", "is_archived": false }`.
   - Возвращает объект с `id` и пустым `extra`.

2. **PUT /api/v1/companies/{id}**
   - Принимает полный payload от фронта.
   - Сохраняет все поля, включая `contacts` и `extra`.
   - Возвращает 200 и актуальный объект компании.

3. **GET /api/v1/companies/{id}**
   - Возвращает карточку полностью, включая `extra` и `contacts`.

4. После сохранения на фронте данные должны отображаться без потерь.

---

## 🧱 Структура таблицы `companies`

| Поле | Тип | Комментарий |
|------|-----|-------------|
| id | UUID (PK) | Уникальный идентификатор |
| name | TEXT | Название компании |
| legal_name | TEXT | Юридическое название |
| tax_id | TEXT | NIP / VAT |
| phone | TEXT | Телефон |
| email | TEXT | Email |
| website | TEXT | Сайт |
| country_code | TEXT | Код страны |
| city | TEXT | Город |
| address | TEXT | Адрес |
| is_archived | BOOLEAN | Флаг архива |
| extra | JSONB | Все дополнительные данные (все новые секции) |

Если поля `extra` нет:

```sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS extra JSONB NOT NULL DEFAULT '{}'::jsonb;
```

---

## ⚙️ API и логика

### PUT `/api/v1/companies/{id}`

- Обновляет базовые поля.
- Если `contacts` присутствуют — сохраняет в `extra.contacts`.
- Если `extra` присутствует — делает **deep merge** (не перезаписывает всё полностью).

Пример merge:

```python
def deep_merge(a: dict, b: dict) -> dict:
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            a[k] = deep_merge(a[k], v)
        else:
            a[k] = v
    return a
```

---

## 🧾 Pydantic-схемы

```python
class CompanyIn(BaseModel):
    name: Optional[str]
    legal_name: Optional[str]
    tax_id: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    country_code: Optional[str]
    city: Optional[str]
    address: Optional[str]
    is_archived: Optional[bool]
    contacts: Optional[list[dict]]
    extra: Optional[dict]
```

```python
class CompanyOut(CompanyIn):
    id: UUID
```

---

## 🧩 Связи и зависимости

**Обязательно проверить и привести к единому формату:**

- `company_id` корректно передаётся в вакансиях и кандидатах.
- При удалении компании:
  - вакансии (`vacancies.company_id`) остаются целыми, либо помечаются как “без компании” (по правилам бизнес-логики).
  - кандидаты, связанные через вакансии, не теряют данные.
- В карточке вакансии отображаются данные компании из обновлённой структуры (`name`, `country_code`, `operations.lanes`, `billing.payment_terms_days` и др.).
- Все API-фильтры (`/vacancies`, `/candidates`) должны использовать новое поле `company_id` без ошибок (проверить SQLAlchemy join’ы и схемы).

---

## ✅ Definition of Done

- [ ] POST /companies — создаёт черновик с id.
- [ ] PUT /companies/{id} — сохраняет все поля.
- [ ] GET /companies/{id} — возвращает весь JSON без потерь.
- [ ] Все поля видны на фронтенде после сохранения.
- [ ] Нет ошибок `405` / `422`.
- [ ] Модули **companies**, **vacancies**, **candidates** связаны и работают синхронно.
- [ ] Проверены все joins и фильтры.
- [ ] Alembic-миграции проходят успешно.
- [ ] Соответствует `/docs/specs/modules/companies.md` и общим канонам HostFlow.

---

## 📁 Проект
**HostFlow**  
Backend: `backend/app/api/v1/companies.py`  
Frontend: `hostflow-frontend/src/pages/Companies.tsx`  
Database: **PostgreSQL 16**

---

## 🧠 Резюме

Нужно:
- Исправить сохранение компаний (все секции `extra`).
- Проверить работу связей `companies ↔ vacancies ↔ candidates`.
- Убедиться, что данные читаются и сохраняются единообразно.
- Полностью протестировать модуль в связке с остальными.

---