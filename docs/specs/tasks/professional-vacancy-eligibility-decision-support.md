# Matching — Professional Vacancy Eligibility / Recruiter Decision Support

**Status:** **READY FOR IMPLEMENTATION** (2026-10-20). The four contract decisions are closed. First production consumer of `professional_requirements_evaluation.v1`. Decision support only. The evaluator is not changed.
**Parent:** [Professional Profile domain](professional-profile-domain-implementation.md), foundation **CLOSED / Production PASS**.
**Source:** `evaluate_professional_requirements` in `backend/app/services/professional_requirements_evaluator.py`. Requirements come from the existing vacancy overlay projection (`professional_requirements` in `backend/app/entity_profile/vacancy_overlay_runtime.py`). Enforcement stays `shadow`.

The recruiter sees vacancy eligibility for one Candidate × Vacancy. The result is `match`, `no_match`, `needs_info`, or `needs_review`. The result does not reject the candidate, change stage, readiness, or handoff, create automation, or block a manual action.

## Allowed effect

Evaluator result → visible vacancy eligibility. No automatic action.

The visible decision is `shadow_eligibility`. It is computed from mandatory requirements only. A preferred requirement stays out of that decision. Its `preference_result` is not a rank and is not a score.

`no_match` remains an explanation. It is not `no_fit` and it is not a pipeline action. The recruiter-facing words are «Не соответствует». The meaning is «Не соответствует требованиям вакансии». The UI never says «Отклонён».

## 1. Where eligibility is shown

The place is the Candidate Card for its active vacancy. It is not the Professional Profile tab. Professional Profile describes the candidate. Eligibility is the relation Candidate × Vacancy. The same candidate can match one vacancy and fail another.

The block sits in the card's right operational rail, beside `CandidateStageDecisionPanel`. The rail is the `rail` slot of `EntityRecordSurface`. The vacancy is the card's current `vacancy_id`, the same vacancy already shown in the card context. The block does not offer a second vacancy picker and does not list every vacancy.

When the card has no vacancy, the block is absent.

Collapsed, the block shows:

- heading «Соответствие вакансии»;
- one status: «Соответствует», «Не соответствует», «Недостаточно данных», or «Требует проверки»;
- a count of confirmed mandatory requirements, such as «Недостаточно данных · 3/5 требований подтверждено»;
- the action «Подробнее», which expands the explanation.

Confirmed means `result` is `match`. The denominator is mandatory requirements only.

The result is also captioned «Соответствие профессиональным требованиям», so it is not read as a new global status of the candidate.

## 2. How the explanation is shown

The expanded state is one row per mandatory requirement. It is not a dump of the evaluator payload.

Each row has a requirement in recruiter language, the row result in the same four status words, the evidence that supports it, and the source in recruiter language.

- «Категория CE — соответствует». «Кандидат: CE». «Источник: квалификация».
- «Опыт ≥ 2 лет — соответствует». «Рассчитано: 2 г. 9 мес.». «Источник: история работы».
- «Тент — недостаточно данных». «В подтверждённой истории опыт не найден».

`reason`, `qualified_code`, provenance identifiers, employment ids, and other system codes are inputs to that mapping. They are not shown to the recruiter.

Duration and catalog labels used in those sentences follow the shared presentation rule in the parent contract. This card does not import them from the Professional Profile feature.

## 3. Coexistence with the legacy evaluator

`evaluate_lead_criteria_v1` keeps the recruitment and routing lifecycle it has now. It receives nothing from this evaluator. Its results stay `fit`, `no_fit`, `needs_info`, and `no_criteria`.

Professional Vacancy Eligibility answers only: how far this candidate's canonical Professional Profile satisfies the professional requirements of this vacancy.

There is no `overall_result` that combines legacy `fit` / `no_fit` with `shadow_eligibility`. The two vocabularies are not merged, and neither result is an input to the other.

If both results are on the same screen, this one is captioned «Соответствие профессиональным требованиям».

## 4. When eligibility is recalculated

The first consumer has no event-driven recalculation and no stored verdict.

Eligibility is a projection of the current vacancy overlay professional requirements × the current Professional Profile. Version 1 computes it on read, when the Candidate × Vacancy context is opened or refreshed.

That read sees changes to licence categories, Code 95, ADR, employment history, calculated tenure, constraints, code mappings, and the vacancy's professional requirements. No invalidation list is required, and a stale stored verdict cannot be shown.

The verdict is not candidate state. A later slice may add a cache only with its own dependency and invalidation contract.

## Implementation scope

- One read projection for one Candidate × Vacancy. It calls the existing overlay requirements and `evaluate_professional_requirements`. It writes nothing.
- Presentation mapping from reason, evidence, and provenance into the recruiter rows above.
- The compact block on the Candidate Card rail.

The evaluator function, its reason codes, and `shadow_eligibility` stay as they are. Ranking, pipeline enforcement, readiness, and handoff are not in this scope.

## Not in this slice

- Ranking. Weight of mandatory against preferred, the relation of `needs_info` to `needs_review`, and comparison of candidates with different completeness are a later slice.
- Workflow and pipeline enforcement. Automatic rejection, stage change, readiness, handoff, automation, and blocking a manual action stay forbidden.
- Readiness and Handoff/HR.
- Changing `evaluate_lead_criteria_v1`, `min_experience_eu_years`, or `years_ce_min`.
- Reopening Professional Profile.
- Caching or storing the verdict.

## Acceptance

A recruiter opens a candidate who has a vacancy and reads the status and the count. «Подробнее» shows one recruiter-language row per mandatory requirement, without system codes. `no_match` is labeled «Не соответствует», never «Отклонён».

With that same `no_match` candidate, the recruiter moves the candidate to the next stage by hand. The transition succeeds. After it, eligibility is still only the visible «Не соответствует». Stage, readiness, handoff, and automation are unchanged by the result. A card with no vacancy shows no eligibility block.
