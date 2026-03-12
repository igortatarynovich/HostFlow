# F7 Scenario B Run Sheet (Agency)

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
- [ ] 3. Business type `agency` selected.
- [ ] 4. Ad source connected.
- [ ] 5. Lead received.
- [ ] 6. Client created.
- [ ] 7. Candidate created.
- [ ] 8. Manager assigned.
- [ ] 9. Team + roles configured.
- [ ] 10. Workflow started end-to-end.

## Evidence

- UI evidence: `<screens/video links or notes>`
- API/log evidence: `<endpoints/log snippets>`
- Notes: `<key observations>`

## Issues

- `<BUG-ID / N/A>`

## Sign-off

- Product: `<name>`
- QA: `<name>`
