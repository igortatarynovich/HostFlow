# GitHub labels — security

Метки используются для фильтрации PR через 6+ месяцев. **Создайте их один раз** в организации/репозитории (веб-UI или GitHub CLI).

## Имена (канон)

| Label | Цвет (suggested) | Смысл |
|-------|------------------|--------|
| `security` | `#B60205` | Любой PR в security perimeter |
| `security-p0` | `#D93F0B` | RLS, auth, public API, миграции |
| `security-rbac` | `#FBCA04` | Роли, permissions, guards |
| `security-rls` | `#1D76DB` | Postgres RLS / tenant context |
| `security-upload` | `#5319E7` | Загрузки файлов / документы |
| `security-public-link` | `#0E8A16` | Публичные ссылки, intake, magic links |

## Создание через GitHub CLI

Из корня репозитория (нужен `gh auth login`):

```bash
gh label create security --color B60205 --force --description "Touches security perimeter (see docs/security)"
gh label create security-p0 --color D93F0B --force --description "RLS, auth, public surface, migrations"
gh label create security-rbac --color FBCA04 --force --description "Roles, permissions, guards"
gh label create security-rls --color 1D76DB --force --description "Postgres RLS / tenant context"
gh label create security-upload --color 5319E7 --force --description "File uploads / documents"
gh label create security-public-link --color 0E8A16 --force --description "Public links, intake, magic links"
```

Флаг `--force` обновляет цвет/описание, если метка уже существует.

## Автоматическое навешивание

Workflow `.github/workflows/pull-request-labeler.yml` (on `pull_request_target`) читает `.github/labeler.yml` и добавляет метки по glob путям. Первый PR с этим workflow **не получит метки на себе** (GitHub выполняет с base branch) — это ожидаемо.

## Связь с CI

`security-gates.yml` не зависит от меток; метки — для людей и отчётности.
