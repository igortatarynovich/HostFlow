# REF-UI-000 — Entity Benchmark Sprint 2

Goal: determine the best baseline for `ENTITY_LAYOUT_V1` using operator-workplace criteria, not visual preference.

Architecture note:

- Structural canon (`Entity Layout`) and execution canon (`Operational Workspace`) are separate systems.
- Reference model: `REF-UI-000-OPERATIONAL_WORKSPACE_MODEL.md`.

Scope (comparison set):

- `detail_candidate_card`
- `detail_vacancy_card`
- `detail_company_card`
- `detail_employee_card`
- `detail_lead_card`

## Scoring Model

- Workflow Support: 20%
- Operator Efficiency: 25%
- Information Architecture: 25%
- Information Density: 15%
- Navigation Flow: 10%
- Extensibility: 5%

Additional mandatory metric:

- Cognitive Load split (1-10 each):
  - Read Load:
    - 1 = current object state is immediately obvious
    - 5 = operator must search for key state signals
    - 10 = state understanding is overloaded/confusing
  - Action Load:
    - 1 = next step is immediately clear
    - 5 = operator must infer what to do next
    - 10 = action path is unclear or fragmented

## Workflow Support Definition

`Workflow Support` evaluates process execution support, not visual polish.

For each entity card, audit:

- can the full primary workflow be executed from the card,
- whether next step is explicit,
- whether blockers are explicit,
- whether missing documents/compliance blockers are explicit (if applicable),
- whether operator must context-switch across multiple screens.

## Required Audit Blocks Per Entity Card

1. Header Zone
- entity title
- status
- primary actions

2. Summary Zone
- key business facts
- metrics/KPI
- immediate health signals

3. Tab Structure
- tab list
- tab depth/nesting
- tab-to-task mapping clarity

4. Section Structure
- order of blocks
- information priority
- scanability

5. Action Surface
- available actions
- action placement
- actions available without deep navigation

6. Source of Truth Analysis
- is the card an authoritative source of truth for this entity lifecycle,
- which data is editable here,
- which data is read-only here,
- which modules depend on this card,
- where duplicated information exists across the system.

7. Dual Quality Evaluation
- Entity Layout Quality: structural clarity and consistency quality.
- Operational Workspace Quality: workflow execution support quality.

## Results Table (to fill during Sprint 2)

| Entity Card | Workflow Support (20%) | Operator Efficiency (25%) | Information Architecture (25%) | Information Density (15%) | Navigation Flow (10%) | Extensibility (5%) | Total Score | Read Load (1-10) | Action Load (1-10) | Benchmark Delta vs Candidate Card |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| detail_candidate_card |  |  |  |  |  |  |  |  |  | 0 |
| detail_vacancy_card |  |  |  |  |  |  |  |  |  |  |
| detail_company_card |  |  |  |  |  |  |  |  |  |  |
| detail_employee_card |  |  |  |  |  |  |  |  |  |  |
| detail_lead_card |  |  |  |  |  |  |  |  |  |  |

## Required Output Per Card Audit

1. Strengths
- why this card helps real operator work.

2. Weaknesses
- what blocks immediate `ENTITY_LAYOUT_V1` adoption.

3. Adaptation Backlog
- concrete improvements required before canonical lock.

4. Dual-Quality Verdict
- explicit conclusion for `Entity Layout Quality`,
- explicit conclusion for `Operational Workspace Quality`.

## Mandatory Sprint 2 Exit Artifact

Before `ENTITY_LAYOUT_V1` lock, Sprint 2 must produce:

- `REF-UI-000-ENTITY_LAYOUT_V1-backlog.md`

This backlog defines required canonical zones and migration-driving adaptations.
It is not a bug list; it is the contract bridge from current best card to canonical layout.

## Sprint 2 Decision Rule

- `ENTITY_LAYOUT_V1` cannot be locked by intuition.
- Candidate card is the benchmark reference for this sprint.
- Final mode is expected to be `Adapt` unless another card objectively wins.
- Winning current card is not sufficient for canonical lock without completed `ENTITY_LAYOUT_V1` backlog.

## Current Working Decision Lock

- `detail_candidate_card` receives interim role: `Primary UX Benchmark`.
- All new/changed entity cards must be compared against candidate card until `ENTITY_LAYOUT_V1` is formally approved.
