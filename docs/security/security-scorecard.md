# HostFlow — Security Scorecard

**Generated:** 2026-08-03T08:05:31Z (UTC)  
**Generator:** `scripts/security/generate_security_scorecard.py`  
**Canon:** [`runtime-roadmap.md`](./runtime-roadmap.md) Phase 8 · [`security-ssot.md`](./security-ssot.md)

Living **repo-derived** scorecard for leadership / retros. Does not replace SSOT invariants. Refresh with `make security-scorecard`.

| Area | Metric | Value | Target | Status | Note |
|------|--------|-------|--------|--------|------|
| Security tests | `backend/tests/security/test_*.py` count | 16 | ≥ 10 | `green` | Unit/integration coverage for isolation, telemetry, detection. |
| CI gates | Required security gate scripts on disk | 6/6 | 6/6 | `green` | All listed gate scripts present. |
| CI gates | Jobs in `.github/workflows/security-gates.yml` | 15 | ≥ 8 | `green` | Inventory only — green workflow on default branch is reviewed in monthly cycle. |
| Threat models | Files under `docs/security/threat-models/` | 17 | ≥ 10 | `green` | threat-model gate enforces updates when surface code changes. |
| Detection | Phase 7 `DetectionRule` entries | 3 | ≥ 3 | `green` | Each rule requires owner + runbook (CI `detection-rules`). |
| RLS | Models with `tenant_id` covered by RLS enable migrations (static) | 47/178 (26%) | ≥ 70% static hint; 100% live DB audit | `yellow` | Approximation from SQLAlchemy models ∩ Alembic RLS table lists / ALTER TABLE. tenant models=178, rls catalog=57. Prefer live pg_policies audit for leadership reporting. |
| RLS | Runtime `TenantEnforcingAsyncSession` guard | present | present | `green` | Python fail-closed execute before bind (Phase 1). |
| MFA | Adoption superadmin + tenant owners | not measured in repo | > 90% (SSOT) | `n/a` | Product/IdP metric — fill during monthly review; not inferred from git. |
| Vulns | Critical/high in sensitive deps | CI (`security-gates`) | 0 critical / policy on high | `n/a` | Tracked by pip-audit / npm audit / Trivy jobs — paste latest green run link in review log. |

## Summary

- Green / OK: **6**
- Yellow: **1**
- Red: **0**
- N/A (manual / CI external): **2**

## Monthly / quarterly review log

Add a bullet when reviewing (do not delete history):

- _2026-07-29_ — scorecard regenerated; reds=0 yellows=1. Paste security-gates run URL + MFA notes here on review.

## How to refresh

```bash
make security-scorecard          # write docs/security/security-scorecard.md
make security-scorecard-check    # fail on drift (CI)
```

