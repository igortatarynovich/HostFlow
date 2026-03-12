# F7 Scenario C Run Sheet (Employer)

Source of truth: `docs/crm-production-readiness-ssot.md` sections `4.2` and `10`.

Date: `YYYY-MM-DD`  
Environment: `staging | production`  
Tenant: `<tenant-id-or-slug>`  
Owner: `<name/role>`

Result: `PASS | FAIL | BLOCKED`  
Blocker: `<if BLOCKED>`

## Step Checklist

- [ ] 1. User registered successfully.
- [ ] 2. Payment step completed (or marked `BLOCKED` if Stripe not available).
- [ ] 3. Business type `employer` selected.
- [ ] 4. Vacancy created.
- [ ] 5. Candidate created.
- [ ] 6. Responsible person assigned.
- [ ] 7. Statuses configured.
- [ ] 8. Work email connected.
- [ ] 9. Hiring workflow started end-to-end.

## Evidence

- UI evidence: `<screens/video links or notes>`
- API/log evidence: `<endpoints/log snippets>`
- Notes: `<key observations>`

## Issues

- `<BUG-ID / N/A>`

## Sign-off

- Product: `<name>`
- QA: `<name>`
