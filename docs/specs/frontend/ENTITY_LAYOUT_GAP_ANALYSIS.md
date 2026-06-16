# ENTITY_LAYOUT_GAP_ANALYSIS

Scope: `detail_candidate_card`  
Purpose: compare current candidate card state vs required `ENTITY_LAYOUT_V1` contract and define V1 adaptation scope.

Input artifacts:

- `detail_candidate_card.audit.md`
- `REF-UI-000-ENTITY_LAYOUT_V1-backlog.md`
- `REF-UI-000-entity-benchmark-sprint2.md`
- `ENTITY_LAYOUT_V1_DRAFT.md`

## 1. Gap Matrix

| Zone | Current Coverage | Required Coverage | Gap | Gap Type | Evidence |
|---|---:|---:|---:|---|---|
| Header Zone | 80% | 100% | -20% | Action overload / priority ambiguity | Header has rich controls but crowded action surface |
| Summary Zone | 70% | 100% | -30% | Distributed state signals | State/risk/next-step split across header + stage panel + rail |
| Workflow Zone | 65% | 100% | -35% | Fragmented execution guidance | Workflow/blockers/next-action visible but not consolidated |
| Information Zone | 88% | 100% | -12% | Scan depth | Strong coverage, but long vertical structure mixes critical/non-critical data |
| Related Objects Zone | 90% | 100% | -10% | Context fragmentation | Relations exist but are scattered across main content and rail |
| Activity Zone | 78% | 100% | -22% | Visibility model | Activity exists (modal + timeline) but lacks persistent compact context |

## 2. Dual Quality Delta Focus

Current dual quality from audit:

- Entity Layout Quality: `86/100`
- Operational Workspace Quality: `83/100`

Primary delta source is operational layer, not base layout frame.

Highest leverage gap cluster:

1. Workflow Zone (`-35%`)
2. Summary Zone (`-30%`)
3. Activity Zone (`-22%`)

## 3. V1 Adaptation Scope

## 3.1 P0 Scope (must complete before ENTITY_LAYOUT_V1 lock)

1. Unified summary strip
- Combine `state + blockers + next step + owner` in one canonical top block.

2. Consolidated workflow decision stack
- Single prioritized sequence for `next action`, blockers, SLA pressure, and required operator move.

3. Canonical blocker hierarchy
- Explicit ordering and severity tiers across docs/contact/vacancy/handoff constraints.

4. Header action budget + overflow
- Define primary action cap and deterministic overflow pattern.

## 3.2 P1 Scope (strongly recommended for V1 readiness)

1. Persistent activity mini-summary
- Show recent activity, overdue count, and timeline freshness inline (without opening modal).

2. Related-objects normalization
- One stable zone for vacancy/company/docs/manager links and status.

3. Progressive disclosure for low-frequency sections
- Reduce read depth for high-frequency operator workflows.

## 3.3 P2 Scope (post-lock optimization)

1. Fine-grained visual prioritization tuning for complex states.
2. Micro-copy harmonization for next-step guidance.

## 4. Backlog Mapping

| Gap | Backlog Link |
|---|---|
| Header -20% | `ELV1-002` + new header-budget task |
| Summary -30% | `ELV1-003` + unified summary strip task |
| Workflow -35% | `ELV1-001` + consolidated blocker stack task |
| Related Objects -10% | New relation-context normalization task |
| Activity -22% | New persistent activity summary task |

## 5. Operational Workspace Priority Statement

For HostFlow, the `83 -> 95` improvement path is primarily operational:

- next action clarity,
- workflow guidance quality,
- blocker visibility and ordering,
- missing data/document signals,
- alerts/SLA pressure coherence.

This confirms that V1 progress is not mainly a visual redesign task.

## 6. Recommendation

- Keep `detail_candidate_card` as `Primary Benchmark + Adapt Candidate`.
- Execute Candidate-card V1 adaptation scope before auditing weaker cards.
- Defer cross-entity comparisons until P0 adaptation scope is specified and accepted.
