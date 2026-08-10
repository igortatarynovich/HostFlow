# Journey checklists (Phase 2.2)

Канон: [`docs/specs/personas.md`](../personas.md) · trust roles [`ADR-036`](../architecture/ADR-036-four-trust-roles-rbac.md).

Каждый файл — чеклист для **одной** QA-сессии. Legacy job-title names in filenames remain for UAT continuity; **trust role** is in the Role/context column.

| Phase | Persona | Trust role / context (ADR-036) | File |
|-------|---------|--------------------------------|------|
| 2.2.C | Administrator | `administrator` · tenant | [administrator.md](./administrator.md) |
| 2.2.D | Team lead | `employee` + preset `team_lead` (legacy journey name supervisor) | [supervisor.md](./supervisor.md) |
| 2.2.E | Recruiter | `employee` + preset `recruiter` | [recruiter.md](./recruiter.md) |
| 2.2.F | Portal guest | `viewer` + `access_context=portal` (legacy client_manager) | [client-manager.md](./client-manager.md) |
| 2.2.G | Portal guest ops | `viewer` + portal (legacy client_processor) | [client-processor.md](./client-processor.md) |
| 2.2.H | Viewer | `viewer` + `access_context=tenant` | [viewer.md](./viewer.md) |
| 2.2.I | Candidate portal | external (non-CRM) | [candidate-portal.md](./candidate-portal.md) |
| 2.2.J | Client portal | branded / portal viewer | [client-portal.md](./client-portal.md) |

**Growth activation (not a UAT persona file):** [self-service-success-path.md](./self-service-success-path.md) — Success Path via guided readiness UI under [ADR-034](../architecture/ADR-034-self-service-public-funnels.md). Launch FAQ: `/faq#launch_troubleshooting`.

**G-6 / Work Hub:** прогоны 2.2.C–H обязаны включать шаг **«Work»** (`/app/work`) и подтверждение фразы acceptance: *«вижу на этой странице свой план дня»* — см. первый шаг в каждом CRM-файле.

**Журнал UAT:** метаданные сессии и дефекты — **[`UAT_DEFECT_LOG.md`](./UAT_DEFECT_LOG.md)** (секции «Метаданные сессий» и «Таблица»); owner/ETA по дефектам — **`docs/SSOT.md` §2.1**.
