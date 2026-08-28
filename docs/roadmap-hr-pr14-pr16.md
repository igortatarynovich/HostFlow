# HR verification roadmap (PR14–PR17)

> **Precedence (added 2026-08-28).** Датированный документ (2026-07-13). Его порядок «PR-INFRA → PR15 → PR17 → PR16» и статус **Next** у PR17 **не действуют** как план: Recruitment → HR handoff теперь v1-блокер 4 с собственным брифом — [`recruitment-hr-minimal-handoff.md`](specs/tasks/recruitment-hr-minimal-handoff.md). Порядок работ ведёт [`sales-to-comms-sequential-queue.md`](specs/tasks/sales-to-comms-sequential-queue.md). Названия ветвей ниже — историческая справка, не активная работа. Спеки PR15/PR16/PR17 остаются полезным входом для брифа блокера.

| PR | Scope | Status |
|----|--------|--------|
| **PR14** | UX/style sequential HR verification | **Done** on employee card (`caseMode` → `HrDataVerificationWorkspace`) |
| **PR-INFRA** | pytest email mock safety | Branch `feat/pr-infra-pytest-email-mock` — **merge first** if tests send mail |
| **PR15** | [Hybrid approve readiness](PR15-unify-hr-approve-readiness.md) | Branch `feat/pr15-hr-approve-readiness` — backend only; **do not expand scope** |
| **PR17** | [Candidate → employee HR handoff](PR17-candidate-to-employee-handoff-spec.md) | **Next** — handoff mapping + filled HR employee card (modules stay separate) |
| **PR16** | [Recruitment package before HR](PR16-recruitment-package-pre-hr.md) | After PR17 Phase A (or explicit exception in PR16 doc) |

**Order:** PR-INFRA → PR15 → **PR17** (surface cleanup) → PR16.

**Rule until PR17 ships:** improve **employee card** and handoff copy — do not add Person Profile or merge HR into candidate routes.
