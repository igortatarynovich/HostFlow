# Candidate Intake via Telegram - Execution Plan

Reference spec:
- `docs/specs/workflows/candidate-intake-via-telegram.md`

## Scope
Implement product flow:
- Meta channels (`whatsapp/messenger/instagram`) for entry and transfer only;
- Telegram for full candidate intake and documents;
- CRM as single source of truth with no duplicated candidate fields.

## Delivery Principles
- One canonical field definition for intake + candidate card.
- Candidate-owned fields are read-only in manager card by default.
- Any manager override requires reason + audit event.
- Each increment must be releasable behind existing feature/role guards.

## Increment 1 - Field Ownership Lock (2-3 days)

Goal:
- freeze canonical ownership rules and map existing fields.

Backend:
- Add `field_contract` to candidate profile config (or derived adapter over profile config).
- Add response endpoint for field contract:
  - `GET /api/v1/candidate-profiles/{id}/field-contract`
- Normalize codes for current intake payload:
  - `contacts.*`, `personal.*`, `experience.*`, `employments[]`, `agreements.*`.

Frontend:
- Add internal helper to consume field contract shape.
- Add read-only rendering mode flag for candidate-owned fields in candidate card.

DoD:
- Field matrix from spec is represented in API payload.
- No unresolved duplicate field codes in mapping.

## Increment 2 - Candidate Card Dedup + Override Audit (3-4 days)

Goal:
- remove duplicate data entry between card and intake.

Backend:
- Add override API semantics:
  - manager can update candidate-owned field only with `override_reason`.
- Write audit record for each override (`actor`, `field_code`, `old_value`, `new_value`, `reason`, `source=manager_card`).

Frontend:
- Candidate card:
  - candidate-owned fields displayed as read-only values by default;
  - explicit `Override` action opens reason input;
  - successful override shows audit marker.

Files likely touched:
- `backend/app/api/v1/candidates/*.py`
- `backend/app/services/audit.py`
- `hostflow-frontend/src/pages/CandidateCard.tsx`
- `hostflow-frontend/src/api/candidates.ts`

DoD:
- Manager cannot silently overwrite candidate-owned fields.
- Override path is auditable and visible.

## Increment 3 - Telegram Intake Step Engine (4-6 days)

Goal:
- ask only missing required fields and persist answers immediately.

Backend:
- Add intake step resolver service based on field contract + current candidate state.
- Extend Telegram webhook command flow:
  - start/resume step;
  - validate answer;
  - persist answer to canonical field;
  - return next question or completion state.
- Persist progress marker in `candidate.intake_state`.

Frontend:
- No mandatory UI changes (server-driven bot flow), but add debug view in admin (optional).

Files likely touched:
- `backend/app/api/v1/communications.py`
- `backend/app/api/public/intake.py`
- `backend/app/services/*telegram*`

DoD:
- Linked candidate can finish required questionnaire in Telegram without portal fallback.
- Resume works after interruption.

## Increment 4 - Telegram Document Completion Loop (4-5 days)

Goal:
- complete required documents through Telegram + scanner.

Backend:
- Add Telegram action that returns WebApp scanner link with candidate/doc context token.
- On scanner upload commit:
  - bind files to required doc types;
  - update checklist completeness;
  - notify candidate about remaining items.

Frontend:
- Ссылка на загрузку документов: публичная анкета `/public/apply/{token}?mode=documents` (legacy PublicScanPage / wasm-камера сняты; см. **`docs/SSOT.md`**).

Files likely touched:
- `backend/app/api/v1/communications.py`
- `backend/app/api/public/intake.py`
- `hostflow-frontend/src/pages/public/PublicIntakeNew.tsx` (и связанные хуки загрузки)

DoD:
- Candidate can upload required docs from Telegram flow.
- Bot reports completion/remaining required docs correctly.

## Increment 5 - Meta Channel Setup Wizard Clarity (3-4 days)

Goal:
- make WhatsApp/Messenger/Instagram setup self-explanatory in `en/ru/pl`.

Frontend:
- For each channel add 4-step in-product setup guide:
  - where to get credentials;
  - what to paste in each field;
  - how to run test;
  - where to set webhook URL/token in provider console.
- Add explicit help copy:
  - WhatsApp `Phone number ID` != human phone number.
- Convert remaining hardcoded strings in messenger settings to i18n keys.

Backend:
- Keep current test-connection contract; return actionable error details.

Files likely touched:
- `hostflow-frontend/src/pages/admin/CommunicationsMessengerSettingsPage.tsx`
- `hostflow-frontend/src/i18n/en.json`
- `hostflow-frontend/src/i18n/ru.json`
- `hostflow-frontend/src/i18n/pl.json`

DoD:
- New user can connect channel without external documentation.
- Setup UX fully localized in 3 languages.

## Increment 6 - Operational Metrics and Trust Report (2-3 days)

Goal:
- measure quality of new flow and detect noise.

Backend:
- Add counters/events:
  - intake started/completed;
  - step drop-off by field;
  - overrides count;
  - docs completion lead time.

Frontend:
- Add compact report block in comms settings or SLA incidents page.

DoD:
- Team can monitor completion, friction, and duplicate overrides.

## Dependencies and Sequence
1. Increment 1
2. Increment 2
3. Increment 3
4. Increment 4
5. Increment 5
6. Increment 6

`Increment 5` can run partly in parallel with `Increment 3/4` (different surfaces), but i18n and setup text should be finalized before release.

## Release Gates
- Backend compile checks for touched modules.
- Frontend:
  - `npm --prefix /opt/HostFlow/hostflow-frontend run i18n:check`
  - `npm --prefix /opt/HostFlow/hostflow-frontend run build`
- Smoke scenarios:
  - Meta lead -> WhatsApp first contact -> Telegram bind -> full intake -> docs -> submitted;
  - manager override with reason and audit trace;
  - channel setup test + webhook copy flow in all three locales.
