# HR verification roadmap (PR14–PR17)

| PR | Scope | Status |
|----|--------|--------|
| **PR14** | UX/style sequential HR verification | **Done** on employee card (`caseMode` → `HrDataVerificationWorkspace`) |
| **PR-INFRA** | [pytest email mock safety](PR-INFRA-pytest-email-mock.md) | Branch `feat/pr-infra-pytest-email-mock` — **merge first** if tests send mail |
| **PR15** | [Hybrid approve readiness](PR15-unify-hr-approve-readiness.md) | Branch `feat/pr15-hr-approve-readiness` — backend only; **do not expand scope** |
| **PR17** | [Candidate → employee HR handoff](PR17-candidate-to-employee-handoff-spec.md) | **Next** — handoff mapping + filled HR employee card (modules stay separate) |
| **PR16** | [Recruitment package before HR](PR16-recruitment-package-pre-hr.md) | After PR17 Phase A (or explicit exception in PR16 doc) |

**Order:** PR-INFRA → PR15 → **PR17** (surface cleanup) → PR16.

**Rule until PR17 ships:** improve **employee card** and handoff copy — do not add Person Profile or merge HR into candidate routes.
