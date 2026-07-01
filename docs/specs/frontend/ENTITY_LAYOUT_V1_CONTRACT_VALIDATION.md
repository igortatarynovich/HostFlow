# ENTITY_LAYOUT_V1_CONTRACT_VALIDATION

Scope: `detail_candidate_card`  
Target contract: `ENTITY_LAYOUT_V1_DRAFT.md`  
Validation type: canonical contract validation (not audit, not implementation backlog)

## Inputs

- `ENTITY_LAYOUT_V1_DRAFT.md`
- `detail_candidate_card.audit.md`
- `ENTITY_LAYOUT_GAP_ANALYSIS.md`

## 1. Zone Contract Validation

| Zone | Contract | Current | Pass |
|---|---|---|---|
| Header | Required | Present (dense action surface) | Yes |
| Summary | Required | Partial (signals distributed, not unified) | No |
| Workflow | Required | Present but fragmented across stage/rail/docs | No |
| Information | Required | Present | Yes |
| Related Objects | Required | Present (fragmented placement) | Yes |
| Activity | Required | Present (modal + timeline context split) | Yes |

## 2. Visibility Contract Validation

| Requirement | Pass | Notes |
|---|---|---|
| Context visible above fold | Yes | Header shows identity/status/ownership context |
| Health visible above fold | No | Health/blocker signals exist but are not consolidated |
| Workflow visible above fold | No | Next action exists, but operator must synthesize across multiple blocks |
| Critical counters visible above fold | Partial | Some counters/signals present; canonical counter strip not unified |
| No-scroll/no-tab/no-modal for critical understanding | Partial | Requires cross-reading stage panel + next action + docs rail |

## 3. Workflow First Validation

Question set (3-second rule):

1. What is happening?
- **Partial**

2. Is there a problem?
- **No (in canonical sense)**

3. What should I do next?
- **Partial**

Result rule:

- If any answer is `No`, workflow-first contract is not fully satisfied.

Validation result:

- Workflow-first contract: **Not Passed**

## 4. Signal Priority Validation

| Check | Pass | Notes |
|---|---|---|
| P0 visible immediately | Partial | Some urgent signals visible, but not consistently consolidated |
| P1 visible immediately | Partial | Process-impacting cues exist but split across zones |
| P2 does not compete with P0 | No | Informational richness can compete with urgent guidance |
| P3 does not clutter critical surface | No | Dense surface increases scan overhead |
| Conflicting duplicate signals absent | Partial | Next-action/health cues appear in multiple surfaces |

## 5. Overall Contract Result

| Result | Meaning |
|---|---|
| Pass | fully matches canonical contract |
| Pass With Gaps | close to canonical; limited contract gaps |
| Major Gaps | significant contract mismatch |
| Fail | requires redesign before alignment |

Current verdict for `detail_candidate_card`:

- **Major Gaps**

Rationale:

- Structural zones mostly exist, but core canonical behavior contracts (summary unification, workflow-first clarity, visibility and priority model) are not yet satisfied.

## 6. Canonicalization Decision Note

- `detail_candidate_card` remains `Primary Benchmark + Adapt Candidate`.
- Validation confirms it is not yet `ENTITY_LAYOUT_V1` compliant.
- Next phase should derive `V1 Adaptation Scope` strictly from these contract gaps.
- Direct migration of other cards to current candidate card is forbidden until `ENTITY_LAYOUT_V1` is contract-compliant.
- Scope bridge artifact: `ENTITY_LAYOUT_V1_IMPLEMENTATION_SCOPE.md`.
