# F7 Scenario A Run Sheet (Solo Services)

Source of truth: `docs/crm-production-readiness-ssot.md` sections `4.2` and `10`.
Run record template: [f7-run-record-template.md](/opt/HostFlow/docs/manual-checklist/f7-run-record-template.md)

Date: `YYYY-MM-DD`  
Environment: `staging | production`  
Tenant: `<tenant-id-or-slug>`  
Owner: `<name/role>`

Result: `PASS | FAIL | BLOCKED`  
Blocker: `<if BLOCKED>`

## Step Checklist

- [ ] 1. User registered successfully.
- [ ] 2. Payment completed (or marked `BLOCKED` if Stripe/webhooks not available).
- [ ] 3. Business type `services` selected.
- [ ] 4. Work email connected.
- [ ] 5. First client created.
- [ ] 6. First message sent.
- [ ] 7. First task created.
- [ ] 8. Auto-reply configured.
- [ ] 9. Workflow started end-to-end.

## Evidence

- UI evidence: `<screens/video links or notes>`
- API/log evidence: `<endpoints/log snippets>`
- Notes: `<key observations>`

## Issues

- `<BUG-ID / N/A>`

## Sign-off

- Product: `<name>`
- QA: `<name>`
