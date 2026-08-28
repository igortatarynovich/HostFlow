# CRM Production Readiness SSOT (Single Source of Truth)

Minimal operational tracker for CI F7 run-log governance. Full readiness matrix lives in linked manual-checklist run sheets.

**Precedence (2026-08-28):** despite the historical title, this file is **not** the authority on whether HostFlow may be released. Release-ready is declared only by the [Release Readiness Gate](specs/gates/release-readiness-gate.md), proven by the [Release Readiness acceptance suite](specs/journeys/release-readiness-acceptance-suite.md). This file remains the operational tracker for the **F7 manual scenario run-log** enforced by the `f7-docs-qa` CI workflow (`scripts/check-f7-run-log.mjs`, `scripts/create-f7-run-record.mjs`) — it is referenced from code and CI and therefore must not be archived or renamed without updating both.

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
