# REF-UI-000 — ENTITY_LAYOUT_V1 Backlog

Purpose: define mandatory canonical operator-workplace structure for all entity cards in HostFlow.

This is not a bug list.
This is a canonical adaptation backlog from best current sample to `ENTITY_LAYOUT_V1`.

Source baseline:

- Primary baseline candidate: `detail_candidate_card`
- Input source: Sprint 2 entity benchmark + per-card adaptation findings

## Canonical Zone Contract (Mandatory)

## 1. Header Zone

Must always include:

- entity title,
- current status,
- owner/assignee,
- quick actions.

Contract goals:

- immediate identity + accountability,
- minimum-click access to top actions.

## 2. Summary Zone

Must always be top-priority and visible near top of card.

Operator must understand within 3 seconds:

- what object this is,
- current state,
- whether there are problems,
- what next action is expected.

Contract goals:

- instant situational awareness,
- reduce initial scan time.

## 3. Workflow Zone

Most important zone for HostFlow.

Must include:

- next step,
- blockers,
- expected actions,
- overdue tasks,
- missing documents/compliance gaps (if applicable).

Contract goals:

- move process forward directly from card,
- avoid context-switching for workflow execution.

## 4. Information Zone

Must include core object data in stable information hierarchy.

Contract goals:

- predictable data placement,
- clear read/edit distinction.

## 5. Related Objects Zone

Must include linked entities relevant to process execution.

Candidate example:

- vacancy,
- company,
- documents,
- manager.

Contract goals:

- preserve lifecycle context,
- reduce navigation hops between modules.

## 6. Activity Zone

Must include audit/activity timeline:

- changes,
- notes,
- events.

Contract goals:

- reliable historical context,
- decision traceability.

## Backlog Structure (How to Fill)

Each backlog item must include:

- `backlog_id`
- `zone`
- `title`
- `problem`
- `impact`
- `proposed_change`
- `priority` (`P0 | P1 | P2`)
- `benchmark_reference`
- `migration_scope` (cards affected)
- `acceptance_criteria`

## Backlog Items (Initial Placeholder)

| backlog_id | zone | title | problem | impact | proposed_change | priority | benchmark_reference | migration_scope | acceptance_criteria |
|---|---|---|---|---|---|---|---|---|---|
| ELV1-001 | Workflow Zone | Next Step prominence | Next action signal is not consistently dominant across cards | Slower operator decisions | Define unified next-step slot with fixed position and visual priority | P0 | detail_candidate_card | all entity cards | Next step visible without tab switch on all cards |
| ELV1-002 | Header Zone | Header action overload control | Header action density can degrade scanability | Higher cognitive load | Define max primary actions + overflow behavior | P1 | detail_candidate_card | all entity cards | Primary actions count and overflow behavior are standardized |
| ELV1-003 | Summary Zone | Summary consistency | Summary composition differs by module | Slower orientation and re-learning | Define summary minimum fields by entity family | P0 | detail_candidate_card | all entity cards | Summary contract present on each entity card |

## Decision Path

`detail_candidate_card (best current benchmark)`

-> `Sprint 2 comparative scoring + cognitive load`

-> `ENTITY_LAYOUT_V1 adaptation backlog`

-> `ENTITY_LAYOUT_V1 canonical lock`

-> `migration of vacancy/company/employee/lead cards`

