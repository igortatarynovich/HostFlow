# A6-S7 Manual Evidence Checklist

Date: `2026-03-15`  
Scope: close manual proof for `buy slot -> create company -> downgrade edge case` on a real tenant.

## 1. Preconditions

- Tenant slug is known (example: `victoria-space`).
- Owner account has access to Billing and My Company.
- Stripe webhook endpoint for production/staging is healthy.

## 2. Baseline Snapshot (Before)

1. Run tenant slot snapshot:

```bash
docker compose exec -T backend python backend/scripts/a6_operating_slots_tenant_snapshot.py \
  --tenant-slug <tenant-slug> \
  --report /app/docs/manual-checklist/a6-s7-slots-snapshot-$(date +%F)-<tenant-slug>-before.md \
  --json /app/docs/manual-checklist/a6-s7-slots-snapshot-$(date +%F)-<tenant-slug>-before.json \
  --label before
```

If `/app/docs` in your container maps to `backend/docs` in host workspace, move files to root `docs/manual-checklist/` after generation.

2. Attach generated files:
- `docs/manual-checklist/a6-s7-slots-snapshot-<date>-<tenant-slug>-before.md`
- `docs/manual-checklist/a6-s7-slots-snapshot-<date>-<tenant-slug>-before.json`

## 3. Manual UI Path (Slot Add + Create)

1. Open `/app/settings/billing?focus=company-slots`.
2. Increase add-on slots (`+` and `Save`).
3. Capture screenshot `billing-before-after-slot-add`.
4. Go to `/app/my-company` or onboarding create flow.
5. Create new `operating` company.
6. Capture screenshot `operating-company-created`.

## 4. Webhook / Invoice Proof

1. Capture backend logs for relevant events:

```bash
docker compose logs backend --since=15m | rg "invoice.paid|customer.subscription.updated|extra_operating_company_slots|OPERATING-COMPANY-LIMIT"
```

2. Save snippet into run-record as API/log evidence.

## 5. Downgrade Edge Case (No Data Loss)

1. Reduce add-on slots in Billing to provoke `used > effective`.
2. Confirm existing operating companies remain visible.
3. Attempt creating one more operating company and confirm blocking path (Billing CTA).
4. Capture screenshot `over-limit-warning` and `create-blocked`.

## 6. Snapshot (After Downgrade)

1. Run tenant snapshot again:

```bash
docker compose exec -T backend python backend/scripts/a6_operating_slots_tenant_snapshot.py \
  --tenant-slug <tenant-slug> \
  --report /app/docs/manual-checklist/a6-s7-slots-snapshot-$(date +%F)-<tenant-slug>-after-downgrade.md \
  --json /app/docs/manual-checklist/a6-s7-slots-snapshot-$(date +%F)-<tenant-slug>-after-downgrade.json \
  --label after-downgrade
```

2. Attach generated files:
- `docs/manual-checklist/a6-s7-slots-snapshot-<date>-<tenant-slug>-after-downgrade.md`
- `docs/manual-checklist/a6-s7-slots-snapshot-<date>-<tenant-slug>-after-downgrade.json`

## 7. Exit Criteria (`A6-S7`)

- UI evidence attached for:
  - slot add in Billing,
  - successful operating-company creation,
  - over-limit warning + blocked create after downgrade.
- API/log evidence attached for Stripe sync (`invoice.paid` and/or `customer.subscription.updated`).
- Before/after tenant snapshots attached and consistent with UI behavior.
- Run-record updated and Product/QA sign-off fields filled.
