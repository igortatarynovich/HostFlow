# REF-UI-000 — UI Reference Inventory

Status: Draft for approval  
Owner: Product + Design + Frontend  
Scope: HostFlow backoffice UI  
Last updated: 2026-05-29

## 1. Purpose

`REF-UI-000` is the reference layer for HostFlow UI.
It records what already exists in production and staging UI without redesigning it.

This artifact must be completed before starting `REF-UI-001`.

## 2. Decision Lock

The following decisions are locked for the full audit phase:

1. `LIST_LAYOUT_V1 = Candidates List`
2. `ENTITY_LAYOUT_V1 = Candidate Card`
3. New UI types are forbidden until audit completion.
4. Allowed exception: critical bugfix without creating a new canonical type.

Interim UX benchmark lock:

- `detail_candidate_card` is the `Primary UX Benchmark` for all entity-card audits until official `ENTITY_LAYOUT_V1` approval.
- Entity-card audits must separately evaluate:
  - `Entity Layout Quality` (structure),
  - `Operational Workspace Quality` (workflow execution).
- Reference model: `REF-UI-000-OPERATIONAL_WORKSPACE_MODEL.md`.

## 3. Registries (Required)

The inventory must include all eight registries below.

## 3.1 PAGE_REGISTRY

Required fields:

- `page_id`
- `route`
- `module`
- `layout_type`
- `owner`
- `status`
- `notes`

## 3.2 COMPONENT_REGISTRY

Required fields:

- `component_id`
- `component_type`
- `variant`
- `modules`
- `usage_count`
- `module_coverage`
- `owner`
- `dependency_links`
- `criticality`
- `business_criticality`
- `replacement_cost`
- `status`
- `notes`

## 3.3 LAYOUT_REGISTRY

Required fields:

- `layout_id`
- `source_page`
- `structure`
- `modules`
- `responsive_support`
- `usage_count`
- `owner`
- `criticality`
- `business_criticality`
- `replacement_cost`
- `status`
- `notes`

## 3.4 PATTERN_REGISTRY

Required fields:

- `pattern_id`
- `pattern_name`
- `trigger`
- `placement`
- `behavior`
- `modules`
- `usage_count`
- `owner`
- `dependency_links`
- `criticality`
- `business_criticality`
- `replacement_cost`
- `status`
- `notes`

## 3.5 CANONICAL_CANDIDATES

Required fields:

- `object_id`
- `object_kind` (`component | layout | pattern`)
- `source`
- `usage_count`
- `module_coverage`
- `quality_score`
- `adoption_score`
- `strengths`
- `weaknesses`
- `rationale`
- `proposed_status`
- `decision` (`adopt | adapt | deprecate`)
- `benchmark_component`
- `benchmark_delta`
- `decision_owner`
- `decision_date`

## 3.6 TOKEN_USAGE_REGISTRY

Required fields:

- `token_usage_id`
- `token_type`
- `value`
- `usage_count`
- `modules`
- `owner`
- `status`
- `notes`

## 3.7 INTERACTION_REGISTRY

Required fields:

- `interaction_id`
- `trigger`
- `result`
- `modules`
- `usage_count`
- `owner`
- `dependency_links`
- `criticality`
- `business_criticality`
- `status`
- `notes`

## 3.8 NAVIGATION_REGISTRY

Required fields:

- `page_id`
- `entry_points`
- `primary_entry_point`
- `exit_paths`
- `modules`
- `owner`
- `criticality`
- `business_criticality`
- `status`
- `notes`

## 4. Status Dictionary

Allowed statuses for registries:

- `Candidate`: found element, can become canonical.
- `Canonical`: approved standard.
- `Legacy`: temporarily allowed, no further evolution.
- `Deprecated`: forbidden for new usage, planned for removal.

No other statuses are allowed.

## 4.1 Audit State Dictionary

Audit progress state is tracked separately from status:

- `Not Audited`: detected in inventory, not reviewed.
- `Audited`: reviewed in audit pass.
- `Validated`: manually confirmed by Product/Design/Frontend.

## 5. Criticality Dictionary

Technical criticality values:

- `high`
- `medium`
- `low`

Business criticality values:

- `P0`: blocks recruiter daily operations.
- `P1`: impacts daily work materially.
- `P2`: used periodically.
- `P3`: secondary impact.

Default lock for audit anchors:

- `LIST_LAYOUT_V1` must be marked `business_criticality = P0`.
- `ENTITY_LAYOUT_V1` must be marked `business_criticality = P0`.

## 6. Usage Analytics Fields (Mandatory)

Every component/layout/pattern row must include:

- `usage_count`
- `module_coverage`
- `owner`
- `dependency_links`
- `criticality`
- `business_criticality`
- `replacement_cost`

Field semantics:

- `usage_count`: number of known UI occurrences.
- `module_coverage`: list of modules using this element.
- `owner`: accountable team or person.
- `dependency_links`: hard dependencies that block replacement.
- `criticality`: `high | medium | low`.
- `business_criticality`: `P0 | P1 | P2 | P3`.
- `replacement_cost`: `high | medium | low`.

## 7. Audit Rules

1. Inventory first, decisions second.
2. Visual preference is not a decision criterion during inventory.
3. Every duplicate must be explicitly marked as duplicate.
4. Every deviation from `LIST_LAYOUT_V1` or `ENTITY_LAYOUT_V1` must be logged.
5. Canonical proposal must be evidence-based via usage analytics.
6. `PATTERN_REGISTRY` stores conceptual UX patterns; `INTERACTION_REGISTRY` stores concrete trigger-result behavior implementations.
7. `TOKEN_USAGE_REGISTRY` must capture factual values before token normalization decisions.
8. Navigation inconsistencies must be explicitly captured in `NAVIGATION_REGISTRY`.

## 7.1 Canonical Selection Priority (HostFlow)

When proposing canonical layouts/components/patterns, evaluation priority is fixed:

1. Operator speed.
2. Information density.
3. Interaction predictability.
4. Visual aesthetics.

Canonical choice is performance-first, not beauty-first.

## 8. Required Output (Gate for REF-UI-001)

`REF-UI-000` is considered complete only when all outputs are delivered:

1. Full list of pages.
2. Full list of components.
3. Full list of layout types.
4. Full list of UX patterns.
5. Duplicate list.
6. Deviation list vs `Candidates List` / `Candidate Card`.
7. Canonical candidate list with rationale.
8. Token usage distribution report.
9. Interaction behavior variance report.
10. Navigation entry-point matrix.

If any output is missing, `REF-UI-001` must not start.

Before `COMPONENT_REGISTRY` reaches audit readiness, these decisions are forbidden:

1. Official `TABLE_V1` approval.
2. Official `FILTER_BAR_V1` approval.
3. Official `STATUS_BADGE_V1` approval.
4. Any `REF-UI-001` component canon lock.

Before `ENTITY_LAYOUT_V1` lock, this artifact is mandatory:

- `REF-UI-000-ENTITY_LAYOUT_V1-backlog.md`

Winning the entity benchmark alone is not sufficient; canonical entity layout requires adaptation backlog completion.

Readiness thresholds before starting `REF-UI-001`:

1. `PAGE_REGISTRY` coverage = 100%.
2. `LAYOUT_REGISTRY` coverage = 100%.
3. `COMPONENT_REGISTRY` coverage >= 80%.
4. `PATTERN_REGISTRY` coverage >= 80%.
5. Deviations vs `LIST_LAYOUT_V1` and `ENTITY_LAYOUT_V1` documented.

If any threshold is not met, `REF-UI-001` is blocked.

## 9. Handover Contract to REF-UI-001

The only allowed inputs into `REF-UI-001` are:

- approved registries from `REF-UI-000`,
- approved status assignments,
- approved canonical candidates.

`REF-UI-001` defines what is allowed to be used.
`REF-UI-000` defines what exists.
