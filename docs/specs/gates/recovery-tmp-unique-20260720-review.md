# Recovery review: `recovery/tmp-unique-20260720` (2026-07-20)

Archive branch only — **do not merge wholesale**.

## Classification

| Artifact | Verdict | Action |
|----------|---------|--------|
| `tmp-hostflow-mig-stash/202607081200_*` … `202607081400_*` | Unique Alembic drafts; revision IDs absent from integration; chain bases on older `202607020001_ra_ext` / merges with `202606300001_funnels_*` | **Do not drop into live chain.** Re-evaluate only if product still needs those schema changes; if yes, rewrite as new revisions on current head `202607190004_thread_result_link_c1` |
| `tmp-hostflow-mig-stash/202608250001_adr018_requirement_policy_pin.py` | Unique; pins `requirement_policy_ref` on candidates; `down_revision` merge of stash tip + old funnels head | Same — obsolete parent graph. Superseded or reinvent on current ADR-018 path if still needed |
| `tmp-HostFlow/.../admin_service.py` | Older than live (live larger); missing later `OwnCompany` import and subsequent edits | **Discard as product source.** Diff against live only if hunting a lost bugfix |
| `tmp-HostFlow/.../metaLeads.ts` | Older than live (lacks `MetaFormRoute` types present on integration) | **Discard** — live is newer |
| `tmp-HostFlow/.../conftest.py` | Older (missing `HOSTFLOW_TEST_LIGHT_STARTUP` and later hardening) | **Discard** |
| `tmp-HostFlow/.../settings.py` | Identical to live | No action |
| `tmp-HostFlow/.../check_meta_oauth_env.py` | Identical to live | No action |

## Outcome

- Keep `recovery/tmp-unique-20260720` as a **git archive** (already on origin).
- Safe to delete plain `/tmp/hostflow-mig-stash` and `/tmp/HostFlow` **after** confirming operators have no local need for the draft migrations.
- No cherry-pick into integration from this review except via a future dedicated ADR-018 / service-order schema PR if product re-requests those columns.
