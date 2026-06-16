# REF-UI-000 — OPERATIONAL_WORKSPACE_MODEL

Purpose: separate operational execution model from entity-structure model in HostFlow UI.

## Architectural Separation

## 1. Entity Layout

Entity Layout is a structural frame.

Typical structural zones:

- Header Zone
- Summary Zone
- Information Zone
- Related Objects Zone
- Activity Zone

Primary question:

- Is the entity represented in a clear, consistent, reusable structure?

## 2. Operational Workspace

Operational Workspace is an execution layer for operator work.

Typical operational zones:

- Context Zone
- Workflow Zone
- Alerts Zone
- Tasks Zone
- Related Objects Zone
- Activity Zone

Primary question:

- Can an operator progress the real business workflow from this screen?

## Canonical Operational Zones

| Zone | Purpose |
|---|---|
| Context Zone | Quickly identify who/what this object is and current responsibility context |
| Workflow Zone | Show next step, current workflow state, and transition path |
| Alerts Zone | Surface blockers, risks, SLA pressure, missing requirements |
| Tasks Zone | Present actionable work queue directly on the screen |
| Related Objects Zone | Keep process-relevant links to dependent entities |
| Activity Zone | Preserve timeline/history for decisions and handoffs |

## Applicability Guidance

Entity Layout may be shared broadly across cards:

- country,
- document,
- vacancy,
- other reference entities.

Operational Workspace is expected for process-heavy entities:

- candidate,
- employee,
- driver,
- vehicle (future),
- recruitment case,
- HR case.

## Audit Rule

For entity-card audits, score separately:

1. Entity Layout Quality
- quality of structural information architecture.

2. Operational Workspace Quality
- quality of workflow execution support.

Both scores are required; one cannot substitute for the other.

## Design Principle

HostFlow is process-execution software, not passive record storage.

Therefore:

- structural consistency (`Entity Layout`) and
- operational effectiveness (`Operational Workspace`)

must be modeled and governed as separate canonical systems, even when currently rendered on one screen.

