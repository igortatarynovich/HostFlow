# Matching — Professional Vacancy Eligibility / Recruiter Decision Support

**Status:** Product contract opened 2026-10-20. First production consumer of `professional_requirements_evaluation.v1`. Decision support only. Implementation is not authorized. A data audit is not this slice.
**Parent:** [Professional Profile domain](professional-profile-domain-implementation.md), foundation **CLOSED / Production PASS**.
**Source:** `evaluate_professional_requirements` in `backend/app/services/professional_requirements_evaluator.py`. Enforcement stays `shadow`.

The recruiter sees vacancy eligibility on the candidate. The result is `match`, `no_match`, `needs_info`, or `needs_review`, with each mandatory requirement and its evidence and reason. The result does not reject the candidate, change stage, readiness, or handoff, create automation, or block a manual action.

## Allowed effect

Evaluator result → visible vacancy eligibility. No automatic action.

The visible decision is `shadow_eligibility`. It is computed from mandatory requirements only. A preferred requirement stays out of that decision. Its `preference_result` is not a rank and is not a score.

Each mandatory row already carries `qualified_code`, `strength`, `expected`, `evidence`, `result`, `reason`, and `provenance`. The explanation shows those facts. It does not add a weight, a sort key, or a second verdict.

`no_match` remains an explanation. It is not `no_fit` and it is not a pipeline action.

## Not in this slice

- Ranking. Weight of mandatory against preferred, the relation of `needs_info` to `needs_review`, and comparison of candidates with different completeness are a later slice. This evaluator does not contain that semantics.
- Workflow and pipeline enforcement. Automatic rejection, stage change, readiness, handoff, automation, and blocking a manual action stay forbidden. They can be considered only after a later acceptance shows that these decisions are stable and understandable to recruiters, and only as its own slice.
- Readiness and Handoff/HR.
- Changing `evaluate_lead_criteria_v1`, `min_experience_eu_years`, or `years_ce_min`.
- Reopening Professional Profile.

## Contract decisions before implementation

These four decisions are the rest of this contract. Code does not start until they are written here.

1. Where the recruiter sees eligibility on the candidate.
2. How the requirement-by-requirement explanation is presented. The content is the mandatory row: requirement, evidence, reason, and result.
3. How this eligibility coexists with `evaluate_lead_criteria_v1`. That evaluator keeps `fit`, `no_fit`, `needs_info`, and `no_criteria`, including its use in lead routing. This slice does not replace it, merge the two vocabularies, or feed one result into the other.
4. Which stored facts and events cause eligibility to be recalculated. Until that list exists, nothing caches a verdict and nothing emits a workflow event from it.

## Acceptance, when implementation is authorized

A recruiter can read the eligibility and the reason for each mandatory requirement on a live candidate and vacancy. Saving or moving the candidate by hand still works when the result is `no_match`. No stage, readiness, handoff, or automation changes because of the result.
