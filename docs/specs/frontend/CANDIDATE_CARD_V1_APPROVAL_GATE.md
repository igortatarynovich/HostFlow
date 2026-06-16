# CANDIDATE_CARD_V1_APPROVAL_GATE

Status: Deferred (conditional use only)  
Scope: Candidate Card V1 structural approval  
Input: `CANDIDATE_CARD_V1_WIREFRAME_SPEC.md`

## Decision Update (2026-05-29)

Candidate Card is currently preserved as production baseline.
This gate is activated only if Candidate Card redesign is formally reopened due to validated defect or proven business upside.

## Purpose

Validate Candidate Card V1 wireframe before any UI implementation starts.

## Gate 1 — Above The Fold

Without scroll, these must be visible:

- Context
- Health
- Next Action
- Blockers
- Critical Counters

Result: `PASS / FAIL`

### Above The Fold Budget (Hard Limit)

Above-the-fold area may include only:

- Context
- Health
- Next Action
- Blockers
- Critical Counters
- Workflow position

All other information is defaulted to lower card zones until explicitly justified by gate criteria.

## Gate 2 — 3 Second Rule

Test user must answer within <=3 seconds:

- What is happening?
- Is there a problem?
- What should I do next?

Result: `PASS / FAIL`

## Gate 3 — Workflow First

Workflow surface is above informational deep sections on first screen.

Result: `PASS / FAIL`

## Gate 4 — Signal Priority

P0 and P1 signals are visually unmissable.

Result: `PASS / FAIL`

## Gate 5 — No Navigation Dependency

Core operation does not require:

- tab switching,
- accordion expansion,
- modal opening.

Result: `PASS / FAIL`

## Gate 6 — North Star Compliance

Wireframe complies with:

- Workflow Beats Data
- Signals Beat Navigation
- Summary Beats Details
- Decision Surfaces First

Result: `PASS / FAIL`

## Above-The-Fold Relevance Filter (Mandatory)

For each element placed above the fold, reviewer must confirm it helps answer at least one:

1. What is happening?
2. Is there a problem?
3. What should I do next?

If element does not support any of the three questions, it must be removed from above-the-fold area.

## Gate Result

Only two final outcomes are allowed:

| Result | Meaning |
|---|---|
| Approved | Implementation backlog may start |
| Rework Required | Return to wireframe refinement |

## Decision Rule

If any gate is `FAIL`, final result is `Rework Required`.

## Architecture Freeze Rule

After creation of this Approval Gate:

- new architecture documents for Candidate Card V1 are forbidden,
- new conceptual principles for Candidate Card V1 are forbidden,
- changes are allowed only if:
  - this gate fails, or
  - pilot implementation reveals a validated defect.

This rule prevents endless architecture expansion and enforces transition to product implementation.
