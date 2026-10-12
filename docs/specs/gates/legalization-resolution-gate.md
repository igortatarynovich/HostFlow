# Legalization Resolution Gate

**Status:** **PASS** (accepted 2026-10-12).  
**Line:** `feat/candidate-card-hero-personal`  
**Machine id:** `legalization_applicability.v1` (`RULE_VERSION` `2026-10-12`)  
**Parents:** [Candidates](../modules/candidates.md) · [Document Hub](../../document-hub/module-scope.md) · [Operator Candidate and Employment Facts](../architecture/operator-candidate-employment-facts.md)

**L0 checklist:** No new P-rule. No Passport or Manifest shape change. No Architecture RFC. No new document store. No second calculation layer.

> Frozen path for this slice: applicability → Hub evidence → legalization resolution → readiness.

---

## Contract

Applicability decides which stay and work bases can apply, and which evidence each basis requires. Document Hub stores the file and its metadata. Legalization resolution evaluates that evidence once. Readiness consumes only the resolved residence and work result.

The rule is the configured basis, exemption, and work-procedure contract in `backend/app/reference/legalization_catalog.py`. `backend/app/reference/legalization_resolution.py` executes a row. A new basis is a new row. It is not a new condition in the Candidate Card or in the resolver.

`readiness_from_resolved` reads the resolved pair and its missing items. It does not read Hub documents again.

---

## Acceptance evidence

Operator E2E on candidate `7a410617-79f9-40a8-b002-19f044e3abf9`, Candidate Card, reloaded after each major state. Poland default checked on a separate card. The local API on port 8010 stopped after these states were recorded. That shutdown does not reopen the gate.

| Check | Evidence |
|---|---|
| Citizenship default | Ukraine: stay Да, work Да. Poland: both Нет, two Подтверждено, no document rows, no manual mark. Reload keeps both. |
| Manual override | Stay Нет shows Установлено вручную. |
| Applicable bases | Ukraine offers visa, visa-free, temporary, permanent, EU long-term, protection, waiting, other. Belarus drops visa-free. Withdrawal Agreement is not offered for those citizenships. |
| Basis and dependency | Temporary residence: one required residence row and one required Децизия воеводы. Reload keeps one decision row. |
| Missing decision | Approved card without a decision: Не хватает: Децизия воеводы. Same after reload. |
| Review | Upload, metadata, review, and approval of the decision: residence Подтверждено. Same after reload. |
| Open file | Открыть returns `GET /api/v1/db/documents/543d7d15-e062-4540-8d01-9620c7aa7df0/file` → `200 application/pdf`. |
| Work and exemption | Work Нет shows Установлено вручную, Требуется проверка, exemption Другое основание. |
| Work permit | Type → order → Заказано (kept on reload) → received → upload → review → both Подтверждено, kept on reload. |
| Employer mismatch | Не соответствует текущему трудоустройству, kept on reload. |
| Citizenship change | Belarus. Hub documents stayed. The manual work override stayed. Applicability was recalculated. |
| Readiness | `ready: false` while work is `needs_verification` with detail `override`. The card badge reads Требуется легализация. |
| Readiness payload | `{ready, blockers[{requirement, status, missing, detail}]}`. No document fields. |
| Reload | Each major state above returned the same result after reload. |

Visual: the collapsed row carries name, requirement, presence, file and status, Открыть, and ⋯. The expanded area is document data only (Данные документа, number, validity, Редактировать). Documents and Personal Data use the same card chrome.

Machine: `backend/tests/reference/test_legalization_catalog.py`, `backend/tests/reference/test_legalization_resolution.py`. An unlisted basis confirms only through its own evidence contract.

---

## Freeze

Do not reopen legalization applicability, evidence resolution, Document Hub ownership, or readiness integration from further Candidate Card work unless a concrete regression shows this contract is broken.

The next Candidate Card slice is outside this gate. This record does not open it and does not add another resolver.
