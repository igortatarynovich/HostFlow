

# Document Templates (Шаблоны документов)

## Цель
Единая система шаблонов (инвойсы, акты, контракты, офферы, сопроводительные письма), рендер в PDF/HTML/Email, многоязычность, версии и лог изменений.

## Подход
- Шаблонизатор: **Jinja2** (переменные, условия, циклы).
- Хранение шаблонов в БД с версиями; файлы активной версии — в S3/минIO.
- Переменные заполняются из контекста: `company`, `contract`, `candidate`, `service_order`, `invoice`, `tenant`.

## Модель данных
- `doc_templates`: `id, tenant_id, code, name, type(html|pdf|email), locale(pl|en|ru|...), active_version_id, is_system, meta`
- `doc_template_versions`: `id, template_id, version, body_markdown|html, variables(json), created_by, created_at`
- `doc_render_jobs`: `id, template_id, version, context(json), status(pending|done|failed), output_file_id?`

## Пример переменных
- Инвойс: `{{ invoice.number }}`, `{{ invoice.issue_date }}`, `{{ client.legal_name }}`, `{{ items }}`.
- Контракт: `{{ company.legal_name }}`, `{{ contract.title }}`, `{{ contract.rate_per_driver }}`.
- Оффер кандидату: `{{ candidate.full_name }}`, `{{ vacancy.title }}`, `{{ company.contacts[0].name }}`.

## API (черновик)
- `POST /templates` / `PATCH /templates/{id}` — CRUD
- `POST /templates/{id}/versions` — новая версия
- `POST /templates/{id}/render` — превью/рендер (PDF/HTML)
- `GET /templates?type=invoice&locale=pl`

## Особенности
- Мультиязык: локализация дат/валют, шаблоны на PL/EN/DE/RU.
- Водяные знаки «Draft/Paid» для инвойсов.
- E-signature (roadmap): интеграция (Autenti/DocuSign) по типам документов.
- Версионирование: сохранение истории, возможность отката.
- Безопасность: только `OWNER/ADMIN` меняют шаблоны; рендер идемпотентен.

## Тест-кейсы
- Рендер инвойса с 2 валютами/ставками VAT.
- Рендер контракта на PL/EN — корректные поля, локализация.
- Откат на предыдущую версию шаблона.
- Ошибка при отсутствии обязательной переменной — информативная.