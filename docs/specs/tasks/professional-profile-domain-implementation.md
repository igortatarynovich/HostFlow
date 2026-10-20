# Professional Profile domain — accepted contract and implementation plan

**Status:** **CLOSED / Production PASS** (2026-10-20). Accepted contract. Schema and resolver PASS. Acquisition Writers PASS. Candidate Card write path PASS. Professional Profile UX PASS. Vacancy professional evaluator (shadow) PASS. End-to-end Intake → Profile → Employment → Resolver → Evaluator PASS. Production interface is `b29a3d2a`. Acceptance is `dc975c34`. Manual smoke on that interface confirmed read, edit, and that saved data persists. The professional requirements evaluator is a shadow read of Overlay predicates × `professional_profile`. It does not enforce `no_fit`, does not move the pipeline, and does not interpret `min_experience_eu_years` or `years_ce_min`. `evaluate_lead_criteria_v1` keeps its current semantics. Professional Profile is not reopened without a concrete defect or a new product requirement. The next slice is [Matching — Professional Vacancy Eligibility / Recruiter Decision Support](professional-vacancy-eligibility-decision-support.md), **READY FOR IMPLEMENTATION**. It shows the evaluator result on the Candidate Card for the active vacancy. It does not rank candidates and does not affect workflow or pipeline. Readiness and Handoff/HR stay later.
**Scope:** schema, compatibility, one aggregation resolver, then the Candidate Professional Profile tab. No automatic rewrite of stored legacy values. Pause stays on UTC. Matching is not switched with the card.

This task records the accepted domain rules and the implementation order. It does not reopen the model.

## Accepted rules

1. `candidate_employments` is the only canonical source of actual work history. `driving_categories`, `operation_scopes`, `movement_patterns`, `crew_modes`, and `work_areas` belong to one employment row.
2. Employer country and trip geography are different facts. `country` is never used to infer where the person drove.
3. Calculated and declared are different provenance. One never overwrites the other. When they disagree, the profile API returns both.
4. A duration is attributed to a facet only when that period can be assigned to the facet unambiguously. Several values in one group produce presence, not copied years.
5. Trailer and equipment in the first version are presence only. Employment length is not trailer tenure.
6. `experience_eu_years` is a contaminated legacy field. It is not the new EU aggregate. `min_experience_eu_years` keeps its current semantics until its own writer/reader migration.
7. Before new experience writes change meaning, every reader and writer of the legacy experience fields is classified `legacy-read`, `compatibility-write`, `migrate`, or `retire`. No big-bang semantic change.
8. Constraints are their own domain: `subject` + `code` + `effect` + `source` + validity. Legalization, a medical document being present, and Hub documents do not create constraints.
9. Preferences and availability are their own structured domain. They are not stored in `extra` and are not employment experience.
10. Matching uses one code vocabulary or an explicit mapping layer. Equal strings are not proof of equal meaning.
11. Tenant timezone is the business calendar. IANA zone is required for a new workspace. Existing Polish workspaces are backfilled to `Europe/Warsaw`. User timezone and communication timezone are not substitutes.
12. Pause remains UTC. `resume_overdue` moves to the workspace calendar in a later slice, after the timezone column exists.

## A. Schema

One Alembic revision family, empty of experience backfill. New employment columns and new tables start empty. Existing `extra` scalars stay byte-for-byte.

### A1. Dictionaries

Closed sets that this slice introduces are rows in `professional_catalog_codes` with `tenant_id` `''` (platform scope, same convention as the field registry). They are not a JSON bag on the candidate.

| Catalog | First codes | Owner |
|---|---|---|
| Driving category | Existing licence category codes | `driver_license_categories`. Not copied |
| Operation scope | `international`, `domestic` | `professional_catalog_codes` |
| Movement pattern | `long_haul`, `distribution` | `professional_catalog_codes` |
| Crew mode | `solo`, `double` | `professional_catalog_codes` |
| Work-area region | `eu`, `cis`, `uk`, `scandi`, `local` | `professional_catalog_codes`. Countries stay on the country registry. These region codes are not equal to free-text `route_types` |
| Trailer / equipment | Not seeded as one list | Three vocabularies stay separate. Mapping rows are not inserted |
| Work system | `2_1`, `3_1`, `4_1`, `6_2`, `8_2`, `no_system`, `individual`, `other` | Hiring field catalog |
| Pay period | `per_day`, `monthly_fixed`, `per_km`, `fixed_plus_bonus` | Hiring field catalog |

Mapping table `professional_code_mappings`: `source_vocabulary`, `source_code`, `target_vocabulary`, `target_code`. Unmapped source codes remain visible as raw presence. They are not dropped and not treated as a target code.

### A2. `candidate_employments` columns

Same JSON-list style as `trailer_types`. The database default `'[]'::jsonb` is a technical empty collection. It means no facts were recorded. It is not a chosen domain value, and it is not a timezone default.

| Column | Shape |
|---|---|
| `driving_categories` | list of driving-category codes |
| `operation_scopes` | list of operation-scope codes |
| `movement_patterns` | list of movement-pattern codes |
| `crew_modes` | list of crew-mode codes |
| `work_areas` | list of `{kind: country\|region, code}` |

Unchanged: `country` (employer), `trailer_types`, `route_types`, `eu_routes`. `eu_routes` is not trip geography.

Employment API accepts the new fields. It does not copy `extra.trailer_types` or `extra.route_types` onto the row.

### A3. Constraints

`candidate_professional_constraints`

| Column | Values |
|---|---|
| `tenant_id`, `candidate_id` | required |
| `subject` | `work_pattern`, `vehicle`, `trailer`, `route`, `geography`, `qualification`, `other` |
| `code` | code inside that subject |
| `effect` | `prohibited`, `limited` |
| `source` | `medical`, `licence`, `operator_recorded`, `document` |
| `valid_from`, `valid_to` | date, nullable; interpreted later in the workspace calendar |
| `note` | text, excluded from matching |

No trigger from legalization, medical presence, or document rows.

### A4. Preferences and availability

`candidate_availability`: one row per candidate, `available_from` date, nullable.

`candidate_preference_choices`: many rows, `subject` + `code`. Geography uses `kind` + `code` with the same shape as `work_areas`. Subjects: `work_system`, `geography`, `operation_scope`, `movement_pattern`, `crew_mode`, `trailer`, `vehicle`.

`candidate_compensation_expectations`: `amount`, `currency`, `period`. Note is not a matching field.

Nothing in this slice reads or writes `extra` for these facts. The legacy `available_from` inside the old candidate-profile blob stays where it is until a named reader moves.

### A5. Tenant timezone

Column `tenants.timezone`, IANA string, no server default.

Data migration: every tenant row that exists at upgrade time is set to `Europe/Warsaw`. That is the Polish-workspace backfill, not a domain default.

After the backfill the column is not null. `create_tenant`, `create_tenant_with_license`, platform admin create, and self-service signup (`backend/app/auth/router.py`) require an explicit zone. Missing or invalid zone is a validation error. User UI timezone and `tenant.settings.communications.channels.timezone` are not read.

Pause is not switched in this revision.

## B. Compatibility

No stored legacy number is rewritten. No calculated value is written back into `extra`.

Declared versus calculated is a read-time classification in the resolver, not a new extra key.

| Signal on the existing row | Declared meaning |
|---|---|
| `intake_state.experience.years_ce` present and equal to `extra.experience_eu_years` | Declared CE, stored in the EU field (`ce_written_as_eu`) |
| No `years_ce`, value present on `experience_eu_years` | Declared under the card label «ЕС» (`operator_eu_label`). Not EU geography |
| Otherwise, `experience_eu_years` present | `ambiguous` |
| `experience_ce_total` | Not declared CE. The card writes it as `experience_eu_years + experience_non_eu_years` |
| `experience_years` | Legacy declared total, only where a writer actually stored it |
| `experience_non_eu_years` | Declared non-EU years from the card |
| `intl_experience` | Declared boolean, not years |
| `extra.trailer_types`, `extra.route_types` | Questionnaire answers, not per-job history |

### Legacy map

Disposition is the end state. Until the slice named in «When», the current write stays.

| Field | Path | Role today | Disposition | When |
|---|---|---|---|---|
| `experience_eu_years` | `backend/app/api/public/intake.py` writes `years_ce` | Writer of CE into the EU field | `compatibility-write` until the four retirement conditions hold, then `retire` | Declared CE from the resolver, Candidate Profile on that projection, CE consumers on CE semantics, EU consumers on calculated EU |
| `experience_eu_years` | Telegram step `years_ce` in `intake_state.py` | Same | same bridge | Same four conditions |
| `experience_eu_years` | `conversion_mapping.py` `years_ce` → extra | Same | same bridge | Same four conditions |
| `experience_eu_years` | Lead normalizer, `_processing.py`, `_reroute.py` | Mixed Europe/CE tokens into the EU field | `compatibility-write` until split; then Europe-only keys stay, CE tokens stop | After origin classification is tested |
| `experience_eu_years` | `CandidateCard` save and `requirementFieldPatch.ts` | Operator write under the EU label | `compatibility-write` | Until the card reads the resolver |
| `experience_eu_years` | Card, experience section, workspace content, lead qualification, profile utils | Display and filters | `legacy-read` | UI slice, one surface at a time |
| `experience_eu_years` | Vacancy `min_experience_eu_years`, readiness bridge, requirement evaluator, `engine_eval_runtime` | Compared as today's stored number, including CE answers | `legacy-read` | Own migration. Do not point these at the new EU aggregate in the schema slice |
| `experience_eu_years` | HR handoff context, recruitment transfer, verified field catalog, document verification, workforce employees, handoff snapshot | Copy the stored number onward | `migrate` | Each consumer switches to the resolver; until then it keeps reading the field |
| `experience_eu_years` | Field registry alias `experience.years_ce` / storage path `extra.experience.years_ce` | Alias does not match the real write path `extra.experience_eu_years` | `retire` the alias | When writers no longer target the EU field |
| `experience_ce_total` | `CandidateCard` save sets the sum of the two year fields | Misnamed total | `retire` the sum write | When the card stops persisting it |
| `experience_ce_total` | Card and workspace content | Display of that sum | `legacy-read` | UI slice. Resolver must not treat it as CE years |
| `experience_years` | Dev seed; card falls back to it when `experience_eu_years` is empty and can then persist that fallback | Legacy total | `legacy-read`, then `retire` | When no reader remains. No new meaning |
| `experience_non_eu_years` | Card edit/save, profile field seed, `profileUtils` | Declared non-EU years | `compatibility-write` and `legacy-read` | Stays declared. Not a calculated geography aggregate |
| `intl_experience` | Public intake, Telegram, conversion mapping, card | Declared flag | `compatibility-write` and `legacy-read` | Stays until `operation_scopes` are what the card shows |
| `extra.trailer_types` | Public intake, both public forms, card chips, candidate list column (client-side on the loaded page) | Questionnaire list | `compatibility-write` and `legacy-read` | Not copied onto employments. Mapping layer only |
| `extra.route_types` | Public intake, card | Questionnaire list (`eu/cis/uk/scandi/local` or free text) | `compatibility-write` and `legacy-read` | Not trip geography |
| `candidate_employments.trailer_types` / `route_types` | Employment API and intake employment rows | Already per-job | Keep | Presence uses these after mapping. Unmapped codes stay raw presence |

Dual-write is not added. `intake_state.experience.years_ce` is already the parallel CE answer; a third CE column would be another truth. New employment attributes have no legacy twin, so they are written only on the employment row.

### Retirement of `years_ce` → `experience_eu_years`

That writer may keep running only as a compatibility bridge for readers that still consume the stored number. It is not an acceptable long-term write.

It is removed when all of the following are true:

1. `professional_profile` returns declared CE from the correct provenance (`ce_written_as_eu` when intake `years_ce` matches the stored number).
2. The Candidate Profile reads that projection.
3. Every consumer that actually needed CE has moved to CE semantics.
4. Every consumer that actually needed EU experience has moved to the calculated EU aggregate.

Consumer Step 3A makes condition 2 true for the Candidate Professional Profile tab. The other three conditions stay open, so the `years_ce` bridge writer remains.

Do not wait until every reader of the string `experience_eu_years` is gone. Classify each reader by the fact it wanted. `min_experience_eu_years` is neither CE nor real EU experience merely because of its name. Its vacancy-criterion meaning is a separate decision and a separate migration. Until that decision, the criterion keeps comparing the stored legacy number.

The writer inventory test records, for every legacy writer: owner, semantic intent, source value, target field, compatibility reason, and this retirement condition. A new writer fails the test. A bridge writer stays visible as removable once its condition is met, and stays required until then.

Resolver Step does not start until this Schema Step is confirmed on its own. The resolver, when it starts, is read-only: it does not write calculated experience back into the candidate, `extra`, or employment rows.

Order in which legacy paths turn off, after schema and the resolver exist:

1. The writer inventory test is already in place from the schema step.
2. Switch one reader at a time to the resolver, after that reader is classified as CE or EU.
3. Remove the `years_ce` → `experience_eu_years` writer when the four conditions above are true.
4. Stop the card from persisting `experience_ce_total` as a sum.
5. Delete a scalar only when its reader list is empty and the declared value is still available from the resolver.

Open debt after Consumer Step 3A: `CandidateCard` save still rewrites the legacy experience scalars when they are already present in `extra`. The Professional Profile tab no longer reads or interprets them. That writer stays on the inventory until the remaining consumers move, and it must not disappear from the retirement list just because this screen stopped displaying it.

Human duration, money format and localized catalog labels belong to a shared presentation layer. The resolver keeps exact days, years and catalog codes. A display such as 5.01 years or `monthly_fixed` is not a reason to change the resolver. The current file `hostflow-frontend/src/modules/professional-profile/presentation.ts` holds those primitives, but that path is feature-scoped. When the first later consumer needs them, duration, money, catalog labels and the unmapped marker move to system/shared ownership. HR Workspace must not import them from the Candidate Professional Profile feature. That move waits for the consumer; it is not a separate refactor.

## C. Aggregation service

One resolver, `professional_profile` service. It reads operator facts, employment rows, constraint rows, preference rows, and the legacy scalars. It does not write them.

Response shape:

| Block | Content |
|---|---|
| `capabilities` | Licence categories, code 95, tachograph, ADR from operator facts. `extra.license_categories` and `extra.has_adr` are not a second capability source |
| `experience.declared` | Classified legacy values and their origin, including both numbers when a calculated value also exists |
| `experience.calculated` | Years only under the unambiguous-period rule, in the workspace calendar once timezone exists |
| `practical_experience` | Equipment presence from employment `trailer_types` after mapping. No years |
| `geography` | `work_areas` only. Employer `country` is returned on the employment record and is absent from this block |
| `work_character` | Scopes, movement patterns, crew modes. Years only when the job has a single value in that group |
| `employments` | Rows, reverse chronology |
| `constraints` | Stored rows. Matching key is `subject` + `code` + `effect` |
| `preferences` | Structured choices and compensation |
| `availability` | `available_from` from `candidate_availability` |

Each calculated aggregate has a status, not a bare null: `calculated`, `presence_only`, `insufficient_history`, `ambiguous_history`, or `no_evidence`. `calculated` carries inclusive days and `years = days / 365` at four decimal places. The other statuses explain why there is no duration. A mixed group is `presence_only` for that facet. An open period whose tenant timezone cannot be read is `insufficient_history` and is not closed with the UTC date. An inverted interval is `ambiguous_history`.

Calculated years:

- Total tenure: merge overlapping employment intervals that have `start_date`. Shared days count once inside that aggregate. An open `end_date` runs to workspace today in `tenants.timezone`. If that zone is missing or invalid, the open period is not measured and UTC is not a substitute.
- CE years: only employments whose `driving_categories` are exactly CE. CE plus another category is presence of CE.
- International years: only employments whose `operation_scopes` are exactly `international`.
- EU years: only employments whose `work_areas` are all EU countries or the `eu` region, and the list is non-empty. `experience_eu_years` is never this number.
- Trailer years: never in this version.

When calculated and declared both exist and differ, both are in the payload. When only one exists, the other is null. The resolver does not pick a winner.

Card, matching, HR, and handoff keep their current reads until a named consumer slice. The first caller of the resolver is its API and the tests below.

## D. Tests

Resolver tests, no UI:

- Overlapping employments count shared days once toward total tenure.
- An open employment uses workspace today, and is omitted while timezone is absent.
- One employment with CE and C yields CE presence and no CE years.
- One employment with only CE yields CE years equal to that employment interval.
- Mixed EU and non-EU `work_areas` yield presence and no EU years.
- Mixed international and domestic yield presence and no international years.
- `experience_eu_years` equal to intake `years_ce` is declared CE origin `ce_written_as_eu`, and the calculated EU block does not use it.
- Declared 7 and calculated 5 are both returned.
- Trailer types `tent` and `frigo` on a four-year job yield presence for both and years for neither.
- Employer `country` does not appear in geography.
- A constraint row is returned; a medical-presence fact alone creates none.
- An unmapped trailer string stays raw presence and does not match a hiring code.

A separate test lists every production writer of the seven legacy keys and fails when a new writer appears outside the compatibility table.

## E. Declared intake

A short driver form records declared professional facts. It does not create a `candidate_employments` row. Calculated tenure still comes only from employment intervals.

`candidate_declared_facts` stores `ce` years, `international` presence, and trailer codes with provenance `candidate_intake`. Operator facts store licence categories, Code 95, and ADR. `candidate_availability` stores `available_from`. Trailer codes use the hiring vocabulary. `professional_code_mappings` maps those codes, plus the legacy intake words `tent` and `frigo`, onto `trailer_hiring`.

Legacy `experience_eu_years`, `years_ce`, and `intl_experience` stay where they are. New intake does not write them. The resolver returns intake declared facts and calculated aggregates together. The evaluator is unchanged and still reads calculated history and operator facts.

Acquisition Writers PASS, 2026-10-20. A short intake answer does not become an employment or a calculated duration. On the Domo-Best check, declared CE stayed 4 years after Domo Route produced calculated total, CE, and international of 1005 days. International experience and curtain were confirmed by that employment. Code 95 stayed an operator fact. The unchanged evaluator matched driving category CE, total tenure of at least 730 days, international presence, trailer hiring curtain, and Code 95. The live Meta question set and the expired trial are deployment, not this slice.

Professional Profile UX PASS, 2026-10-20, revision `b29a3d2a`. On the live Profile Check card the experience block reads as calculated tenure, then experience character, then work history. Declared CE 4 stays beside calculated 2 years 9 months. Availability edits from the date row with save and cancel. Employer country uses the country catalog, and employment licence categories use the same licence catalog as qualification.

Foundation slice **CLOSED / Production PASS**, 2026-10-20. `b29a3d2a` is the verified production interface. `dc975c34` records acceptance. Manual smoke confirmed read, edit, and persistence. Professional Profile stays closed without a concrete defect or a new product requirement. The next slice is [Matching — Professional Vacancy Eligibility / Recruiter Decision Support](professional-vacancy-eligibility-decision-support.md), **READY FOR IMPLEMENTATION**. Its allowed effect is to show the evaluator result to the recruiter on the Candidate Card. Ranking and workflow or pipeline enforcement are later slices.

## Out of this plan

Professional Profile UI was originally outside this plan. It is delivered and accepted in the closed foundation. It is not open work.

- Rewriting stored `experience_*` values.
- Changing `min_experience_eu_years`.
- Moving `resume_overdue` off UTC.
- Employee Workspace.
- Making Hub documents or legalization emit constraints.
