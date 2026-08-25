# CRM Production Readiness SSOT (Single Source of Truth)

Minimal operational tracker for CI F7 run-log governance. Full readiness matrix lives in linked manual-checklist run sheets.

## 10. F7 Scenario Execution Board (A/B/C)

Дата: `2026-07-14`  
Протокол: [f7-scenario-protocol.md](manual-checklist/f7-scenario-protocol.md)

| Сценарий | Статус | Блокер | Комментарий |
|---|---|---|---|
| A — Solo (`services`) | `IN_PROGRESS` | Manual run + sign-off | Stage 1A integration line; formal E2E pending |
| B — Agency (`agency`) | `IN_PROGRESS` | Manual run + sign-off | Stage 1A integration line; formal E2E pending |
| C — Employer (`employer`) | `IN_PROGRESS` | Manual run + sign-off | Stage 1A integration line; formal E2E pending |

### 10.1 Журнал прогонов (операционный)

| Дата | Сценарий | Окружение | Tenant | Результат | Evidence | Owner |
|---|---|---|---|---|---|---|
| `2026-07-14` | A (`services`) | staging | `ci-smoke` | `IN_PROGRESS` | Bootstrap record for Stage 1A CI gate | Eng/CI |
| `2026-07-14` | B (`agency`) | staging | `ci-smoke` | `IN_PROGRESS` | Bootstrap record for Stage 1A CI gate | Eng/CI |
| `2026-07-14` | C (`employer`) | staging | `ci-smoke` | `IN_PROGRESS` | Bootstrap record for Stage 1A CI gate | Eng/CI |

### 10.2 Next Actions Для `F7`

1. Провести ручной E2E прогон сценария `B` и записать `PASS/FAIL` + evidence в `10.1`.
2. Провести ручной E2E прогон сценария `C` и записать `PASS/FAIL` + evidence в `10.1`.
3. Провести ручной E2E прогон сценария `A` и записать `PASS/FAIL` + evidence в `10.1`.
