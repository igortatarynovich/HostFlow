# detail_candidate_card.audit

Artifact: Sprint 2 first real audit  
Component: `detail_candidate_card`  
Route: `/app/candidates/:id`  
Date: 2026-05-29

## 1. Entity Layout Analysis

### Header

- Strong: `CandidateHeader` has stage tag, next-action badge, profile state, waiver badges, favorite, handoff state/action, activity action, edit/delete flow.
- Weak: action density is high; multiple secondary controls compete with primary actions.

### Summary

- Strong: top area surfaces stage, next action, profile availability, handoff status, and key warnings.
- Weak: summary signals are distributed between header, stage panel, and rail; no single compact summary block with explicit "state + risk + next step" grouping.

### Information

- Strong: broad domain coverage via structured sections (`Basic`, `Personal`, `Status`, `Custom Fields`, `Experience`, `Employer`, `Applications`).
- Weak: long vertical card; critical and non-critical data are mixed, increasing scanning depth.

### Related Objects

- Strong: vacancy/company links, applications, unified inbox, services, docs, handoff clients are integrated.
- Weak: relation signals are present but fragmented across main column and rail.

### Activity

- Strong: dedicated activity modal + timeline data (stage history, notes, reminders).
- Weak: activity is one click away, not persistently visible as compact inline signal.

## 2. Operational Workspace Analysis

### Workflow

- Strong: workflow is explicit through `CandidateStageDecisionPanel`, pipeline movement, and stage gating.
- Strong: `NextAction` rail computes next step and supports task creation.

### Alerts

- Strong: document/pipeline blockers, handoff constraints, override states, and error banners are implemented.
- Weak: alerts are distributed across header, stage panel, next-action, docs rail, and toasts; prioritization can feel fragmented.

### Tasks

- Strong: reminders/activities are first-class with create/complete/snooze flows and automation for docs verification tasks.
- Weak: task context is partly split between rail panel and modal timeline.

### Next Actions

- Strong: dedicated `CandidateNextActionPanel` + badge in header; supports stage-driven hints.
- Weak: "what to do now" can still require cross-reading stage panel + docs panel + reminders in complex states.

### Blockers

- Strong: blockers are explicit (docs, vacancy pipeline, contact attempt, handoff conditions).
- Weak: blocker hierarchy is not always presented as one consolidated decision stack.

## 3. Source of Truth Analysis

### Is candidate card a source of truth?

- Yes, for operational candidate lifecycle state.
- It owns critical transitions: stage/status reasons, reminder/task operations, notes, handoff initiation, docs-related workflow actions, and core candidate fields.

### Module dependencies (observed)

- Candidates core data and cache.
- Documents (drawer/panel, docs progress, upload links, blockers, overrides).
- Communications (inbox deep-link).
- Workflow/Handoff (handoff status, client availability, transfer actions).
- Services (service orders section).
- Profiles/Funnels/Gates (candidate profile, stage constraints).

### Duplication and split ownership risks

- Next-action logic exists both as header badge and rail panel.
- Timeline context is split between rail notes/reminders and separate activity modal.
- Some critical state (blockers/risk/next step) appears in multiple places with different visual emphases.

### Data that should remain anchored here

- Candidate lifecycle stage decisions.
- Candidate-specific blockers and next action.
- Candidate handoff state and transfer actions.
- Candidate operational note/reminder context.

## 4. Cognitive Analysis

- Read Load: **6/10**
  - Rich data coverage is strong, but understanding current global state requires scanning multiple zones.
- Action Load: **5/10**
  - Core actions are available, but in complex cases operators still synthesize guidance from several panels.

## 5. Strengths

- Most complete operator-facing workspace in current HostFlow UI.
- Strong integration of workflow, docs, tasks, and cross-module actions.
- Explicit stage progression and blocker-aware behavior.
- High operational depth without leaving the card.

## 6. Weaknesses

- Header and top-level controls are dense.
- Summary and alert signals are distributed, not unified.
- Long page structure increases scan cost.
- Critical workflow cues are sometimes duplicated across zones.

## 7. Adaptation Backlog

1. Consolidate a canonical top summary strip (`state + blockers + next step + owner`) for 3-second orientation.
2. Define header action budget and overflow pattern to reduce top-zone crowding.
3. Introduce consolidated blocker stack with explicit priority ordering.
4. Standardize persistent compact activity summary (last action + overdue count + timeline delta).
5. Normalize relation context block (vacancy/company/manager/docs) into a single predictable location.
6. Reduce section depth by grouping low-frequency data under progressive disclosure.
7. Harmonize next-action signals between header badge and rail into one canonical decision source.

## 8. Dual Quality Verdict

- Entity Layout Quality: **86/100**
- Operational Workspace Quality: **83/100**

Rationale:

- Layout is strong but not yet canonical-grade due to scan complexity and zone overlap.
- Workspace support is best-in-system, but needs consolidation of summary/blocker/next-step signals.

## 9. Recommendation

- **Adapt**

Decision note:

- `detail_candidate_card` is the strongest current benchmark and should remain `Primary UX Benchmark`.
- Do not lock `ENTITY_LAYOUT_V1` yet; complete adaptation backlog first, then re-score against other entity cards.
- Gap-to-scope bridge artifact: `ENTITY_LAYOUT_GAP_ANALYSIS.md`.
