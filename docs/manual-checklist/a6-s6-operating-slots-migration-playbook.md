# A6-S6 Operating Slots Migration / Rollback Playbook

## Scope
- Transition existing tenants to canonical entitlement key for operating company add-on slots:
  - canonical key: `extra_operating_company_slots`
  - legacy aliases: `additional_operating_company_slots`, `operating_company_addon_slots`
- Preserve data-integrity for tenants where `used operating companies > effective limit`.

## Preconditions
1. Backend deployed with:
   - effective slot enforcement in company creation,
   - billing summary returning `company_slots`,
   - webhook sync from Stripe subscription item quantity.
2. Stripe runtime config prepared (if used):
   - `STRIPE_PRICE_OPERATING_COMPANY_SLOT`.
3. DB backup and point-in-time recovery window confirmed.

## Dry-run
Run from repo root:

```bash
python3 backend/scripts/a6_operating_slots_migration_dry_run.py \
  --report docs/manual-checklist/a6-s6-operating-slots-dry-run-$(date +%F).md \
  --json docs/manual-checklist/a6-s6-operating-slots-dry-run-$(date +%F).json
```

Expected output:
- Per-tenant matrix with included/extra/effective/used values.
- Explicit list of overflow tenants.
- Legacy-key presence audit.

## Transition Procedure
1. Execute dry-run and review overflow list.
2. Decide overflow policy with Product/Billing:
   - strict enforcement only (no auto-grant), or
   - temporary grace (`extra_operating_company_slots = suggested_extra_no_data_loss`).
3. Normalize keys (non-destructive):

```bash
python3 backend/scripts/a6_operating_slots_migration_dry_run.py --apply-normalize-keys
```

4. Re-run dry-run; ensure:
   - `legacy_keys_present = 0`,
   - no unexpected changes in `used/effective`.
5. Run manual smoke:
   - tenant at limit cannot create new operating company,
   - tenant with free slot can create,
   - billing shows accurate `included + extra`.

## Rollback (Manual)
If issues detected after normalization:
1. Stop rollout and keep creation guardrails active.
2. Restore previous tenant settings from DB backup / PITR.
3. If partial rollback required, patch affected tenants with SQL (Postgres):

```sql
-- Example: restore previous extra slot value for one tenant.
UPDATE tenants
SET settings = jsonb_set(
  COALESCE(settings, '{}'::jsonb),
  '{billing,subscription,extra_operating_company_slots}',
  to_jsonb(2),
  true
)
WHERE id = '<tenant-id>';
```

4. Re-run dry-run report and compare with pre-rollout report.
5. Keep webhook sync enabled; rollback only entitlement value mapping, not event processing.

## Exit Criteria (`A6-S6 DONE`)
- Dry-run report attached to SSOT evidence.
- Legacy key aliases removed from active tenant payloads.
- Overflow policy explicitly documented and approved.
- Rollback rehearsal documented with timestamp and owner.
