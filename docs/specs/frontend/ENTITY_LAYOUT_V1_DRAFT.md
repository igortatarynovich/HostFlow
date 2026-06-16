# ENTITY_LAYOUT_V1_DRAFT

Status: Draft (canonical contract candidate)  
Layer: Canonical Contract (between Reference and Implementation)  
Scope: HostFlow entity cards

North star reference:

- `HOSTFLOW_UX_NORTH_STAR.md`

## Purpose

Define canonical `ENTITY_LAYOUT_V1` as a contract.

This draft does not define:

- pixel values,
- Figma composition,
- React/Tailwind implementation.

It defines mandatory zones and mandatory information/action contract.

## Zone Contract

## 1. Header Zone

Mandatory elements:

- Entity Name
- Primary Status
- Owner
- Quick Actions

Contract intent:

- operator identifies object and responsibility immediately,
- top actions are available without deep navigation.

## 2. Summary Zone

Mandatory elements:

- Current State
- Health
- Missing Data Count
- Open Tasks Count

Contract intent:

- 3-second orientation: what this object is, how healthy it is, whether immediate attention is required.

## 3. Workflow Zone

Mandatory elements:

- Next Action
- Current Stage
- Blockers
- SLA Warnings

Contract intent:

- workflow progression is explicit and actionable,
- blockers and urgency are visible before lower-priority content.

## 4. Information Zone

Mandatory elements:

- Core Entity Data

Contract intent:

- structured, predictable canonical object data,
- clear separation between editable and read-only information.

## 5. Related Objects Zone

Mandatory elements:

- Linked Records

Contract intent:

- process context remains local to card,
- related entities are accessible without workflow disruption.

## 6. Activity Zone

Mandatory elements:

- Timeline
- Notes
- Audit Events

Contract intent:

- decision traceability,
- continuity across handoffs and role changes.

## Visibility Contract

## Above The Fold Zone (Mandatory)

Without scrolling, tab switching, or modal opening, the operator must see within first 3 seconds:

1. Context
- who/what this object is,
- current status,
- owner.

2. Health
- whether problems exist,
- whether blockers exist,
- whether overdue items exist.

3. Workflow
- what to do next.

4. Critical Counters
- missing documents count,
- open tasks count,
- overdue count,
- other critical process counters if applicable.

This contract is mandatory for all cards mapped to `ENTITY_LAYOUT_V1`.

## Signal Priority Model

All card signals must be classified by priority:

| Priority | Meaning |
|---|---|
| P0 | Immediate action required |
| P1 | Process-impacting signal |
| P2 | Informational signal |
| P3 | Reference/background signal |

Priority rules:

1. P0/P1 signals must be visible in Above The Fold zone.
2. P2/P3 signals must not visually compete with P0/P1 signals.
3. Conflicting signals across zones are forbidden.

## Workflow First Rule

HostFlow cards must follow workflow-first sequencing:

- first: what should be done now,
- second: what data supports that decision.

Design principle:

- Not `Data -> Work`
- But `Work -> Data`

Operator-first decision loop:

1. What is happening?
2. Is there a problem?
3. What should I do next?

This rule is governed by `HOSTFLOW_UX_NORTH_STAR.md`.

## Validation Rules (Draft)

1. Every entity card mapped to `ENTITY_LAYOUT_V1` must implement all 6 zones.
2. Mandatory elements in each zone cannot be omitted.
3. Zone order must preserve operator priority:
   - Header -> Summary -> Workflow -> Information -> Related Objects -> Activity.
4. Workflow Zone signals must be visible without requiring tab-level navigation.
5. Summary and Workflow signals must not be duplicated with conflicting meaning.
6. Above The Fold visibility contract is mandatory.
7. P0/P1 signals must be visible and unambiguous before any deep information sections.

## Usage in Current Phase

This draft is used to compare:

- Current state (`detail_candidate_card.audit.md` + `ENTITY_LAYOUT_GAP_ANALYSIS.md`)
- Target state (`ENTITY_LAYOUT_V1_DRAFT` contract)

Only after this draft is approved:

- produce `ENTITY_LAYOUT_V1_IMPLEMENTATION_BACKLOG.md`
