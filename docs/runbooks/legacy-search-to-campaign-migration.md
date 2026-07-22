# Runbook: Legacy Search → Campaign / Flight migration (PR-A)

**Status:** operational runbook (L3)  
**Canon:** [`ADR-024`](../specs/architecture/ADR-024-acquisition-campaigns-intake-routing.md), [`docs/acquisition/module-scope.md`](../acquisition/module-scope.md)  
**Script:** `backend/scripts/migrate_legacy_searches_to_campaigns.py`  
**Service:** `backend/app/acquisition/legacy_search_migration.py`

## Purpose

Backfill real legacy Searches (Vacancy + acquisition settings) into Marketing Campaign + one V1 Flight **before** removing the Searches operator UI (PR-B / #139).

## Hard rules

- Migrate **only** vacancies with acquisition signals (form / launch_search / non-static `acquisition_v1` activity / `meta_ads_map`).
- Receiver is **`CampaignTarget`** (`target_type=vacancy`, `route_intent=candidate_application`) — no `destination_type` / `destination_id`.
- Idempotency = stamp `vacancies.extra.legacy_search_migration_v1` only. **No** Activity Timeline marker events.
- Rollback archives Campaign and **keeps** stamp (`rolled_back_at`, `campaign_archived=true`). Re-apply after rollback → `already_existed_rolled_back` (no duplicate).
- Do not delete or rewrite legacy `acquisition_v1` / form / Meta ads map (except stamp keys).

## Procedure (production DB copy)

```bash
# From repo root, backend env with DB URL pointing at the copy:
python backend/scripts/migrate_legacy_searches_to_campaigns.py --json /tmp/legacy-search-dry.json
# Review summary: found / needs_manual / false-positive risk

python backend/scripts/migrate_legacy_searches_to_campaigns.py --apply --json /tmp/legacy-search-apply.json
python backend/scripts/migrate_legacy_searches_to_campaigns.py --apply --json /tmp/legacy-search-apply-2.json
# Second apply must create 0 new Campaigns (already_existed only)
```

Optional filters: `--tenant-id`, `--vacancy-id`.

Rollback (stamp retained):

```bash
python backend/scripts/migrate_legacy_searches_to_campaigns.py --rollback --apply --json /tmp/legacy-search-rollback.json
```

## Merge gate checklist

| Check | Requirement |
|-------|-------------|
| Eligible | Every selected Vacancy has a confirmed acquisition signal |
| False positives | 0 bare vacancies received a Campaign |
| Targets | Each Campaign primary target = source Vacancy |
| Company scope | `tenant_id` + `own_company_id` match Vacancy |
| Forms | Valid forms attached |
| Meta | Unambiguous sources bound; others `needs_manual` |
| Status | Campaign/Flight match status mapping |
| Idempotency | Second apply creates 0 new objects |
| Routing | Active Campaign + Flight attribute a new submit |
| Rollback | No attribution loss; no duplicate on re-apply |

## After PASS

1. Merge PR-A.  
2. Unblock PR-B (#139): remove Searches from nav, redirects, Marketing on shell.
