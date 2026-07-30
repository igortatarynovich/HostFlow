# Journey checklists (Phase 2.2)

Канон: `docs/specs/personas.md` § Acceptance. Каждый файл — чеклист для **одной** QA-сессии: оператор проходит шаги, ставит `[x]`, фиксирует баги внизу.

| Phase | Persona | Role / context | File |
|-------|---------|----------------|------|
| 2.2.C | Administrator | CRM `administrator` (Solo → `admin_solo`; Team → `admin_team`) | [administrator.md](./administrator.md) |
| 2.2.D | Supervisor | `supervisor` | [supervisor.md](./supervisor.md) |
| 2.2.E | Recruiter | `recruiter` (agency tenant) | [recruiter.md](./recruiter.md) |
| 2.2.F | Client manager | `client_manager` | [client-manager.md](./client-manager.md) |
| 2.2.G | Client processor | `client_processor` | [client-processor.md](./client-processor.md) |
| 2.2.H | Viewer | `viewer` | [viewer.md](./viewer.md) |
| 2.2.I | Candidate portal | external portal user | [candidate-portal.md](./candidate-portal.md) |
| 2.2.J | Client portal | branded billing / portal | [client-portal.md](./client-portal.md) |

**Growth activation (not a UAT persona file):** [self-service-success-path.md](./self-service-success-path.md) — Success Path + Setup Wizard under [ADR-034](../architecture/ADR-034-self-service-public-funnels.md).

**G-6 / Work Hub:** прогоны 2.2.C–H обязаны включать шаг **«Work»** (`/app/work`) и подтверждение фразы acceptance: *«вижу на этой странице свой план дня»* — см. первый шаг в каждом CRM-файле.

**Журнал UAT:** метаданные сессии и дефекты — **[`UAT_DEFECT_LOG.md`](./UAT_DEFECT_LOG.md)** (секции «Метаданные сессий» и «Таблица»); owner/ETA по дефектам — **`docs/SSOT.md` §2.1**.
