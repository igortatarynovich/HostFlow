# FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN

Status: Complete  
Date: 2026-05-29  
Input: `FOUNDATION_V1.md` (locked)  
Purpose: define how `FOUNDATION_V1` becomes a real standard, not a document.

## Question Answered

> Как FOUNDATION_V1 станет реальным стандартом, а не просто документом?

---

## 1) Current State (Baseline)

Scan date: 2026-05-29. Scope: `hostflow-frontend/src`.

| Category | Allowed uses | Legacy uses | Deprecated uses |
|---|---:|---:|---:|
| Spacing | ~9850 | 36 | **834** |
| Typography | ~5345 | 238 | **47** |
| Colors | ~11000 | — | **655** |
| Radius | ~1777 | 222 | **426** |
| Shadow | ~393 | 12 | **123** |
| **Total** | — | ~506 | **2085** |

**2085 deprecated uses** across the codebase must reach **0** before migration is complete.

---

## 2) Migration Plan (Quantitative)

### 2.1 Spacing — Deprecated (834 → 0)

| Token | Uses | Migration Target | Priority | Files Est. |
|---|---:|---|---|---:|
| `1.5` | 472 | → `2` | **P0** | ~80 |
| `2.5` | 189 | → `2` or `3` | **P1** | ~40 |
| `5` | 126 | → `4` or `6` | P1 | ~25 |
| `3.5` | 16 | → `3` or `4` | P2 | ~10 |
| `24` | 20 | → `8` or layout refactor | P2 | ~8 |
| `7` | 6 | → `6` or `8` | P3 | ~4 |
| `16` | 2 | → `8` or `12` | P3 | 2 |
| `20` | 1 | → nearest canon | P3 | 1 |
| `32` | 1 | → nearest canon | P3 | 1 |
| `96` | 1 | remove | P3 | 1 |

**Phase 1 (P0):** `1.5` alone = 57% of spacing debt (472 uses).  
**Phase 2 (P1):** `2.5` + `5` = 315 uses.  
**Phase 3 (P2–P3):** remaining 47 uses — trivial.

### 2.2 Spacing — Legacy (36, no new uses)

| Token | Uses | Context |
|---|---:|---|
| `10` | 26 | Auth, public, onboarding shells |
| `12` | 10 | Auth, public, onboarding shells |

Legacy spacing: freeze new usage; migrate opportunistically when touching auth/public pages.

### 2.3 Typography — Deprecated (47 → 0)

| Token | Uses | Migration Target | Priority |
|---|---:|---|---|
| `leading-snug` | 37 | → `leading-tight` | P1 |
| `text-4xl` | 4 | → `text-2xl` or remove | P3 |
| `text-6xl` | 2 | → `text-2xl` or remove | P3 |
| `leading-6` | 2 | → `leading-relaxed` | P3 |
| `leading-4` | 1 | → `leading-tight` | P3 |
| `leading-5` | 1 | → `leading-tight` | P3 |

### 2.4 Typography — Legacy (238, no new uses)

| Token | Uses | Note |
|---|---:|---|
| `text-base` | 98 | Prose only |
| `text-3xl` | 40 | → `text-2xl` on touch |
| `font-bold` | 80 | → `font-semibold` |
| `font-normal` | 11 | Reset only |
| `leading-none` | 9 | Heading reset |

### 2.5 Colors — Deprecated Families (655 → 0)

| Family | Uses | Migrate to | Priority | Top Token |
|---|---:|---|---|---|
| `red-*` | 202 | `rose-*` | **P0** | `red-600` (71) |
| `indigo-*` | 122 | `blue-*` | P1 | `indigo-50` (30) |
| `sky-*` | 102 | `blue-*` | P1 | `sky-50` (27) |
| `green-*` | 101 | `emerald-*` | P1 | `green-700` (21) |
| `violet-*` | 38 | `blue-*` | P2 | `violet-200` (8) |
| `teal-*` | 22 | `emerald-*` | P2 | `teal-600` (8) |
| `purple-*` | 19 | `blue-*` | P2 | `purple-100` (5) |
| `gray-*` | 18 | `slate-*` | P2 | — |
| `orange-*` | 16 | `amber-*` | P3 | — |
| `yellow-*` | 8 | `amber-*` | P3 | — |
| `cyan-*` | 7 | `blue-*` | P3 | — |

**Phase 1 (P0):** `red-*` → `rose-*` (202 uses, single-family swap).  
**Phase 2 (P1):** `indigo` + `sky` + `green` (325 uses).  
**Phase 3 (P2–P3):** remaining 128 uses.

### 2.6 Radius — Deprecated (426 → 0)

| Token | Uses | Migration Target | Priority |
|---|---:|---|---|
| `rounded-md` | 265 | → `rounded` or `rounded-lg` | **P0** |
| `rounded-2xl` | 161 | → `rounded-xl` | P1 |

### 2.7 Shadow — Deprecated (123 → 0)

| Token | Uses | Migration Target | Priority |
|---|---:|---|---|
| `shadow` (default) | 70 | → `shadow-sm` | P1 |
| `shadow-lg` | 35 | → `shadow-md` | P2 |
| `shadow-2xl` | 14 | → `shadow-xl` | P2 |
| `shadow-inner` | 4 | remove | P3 |

### 2.8 Migration Phases (Summary)

| Phase | Scope | Deprecated Uses | Cumulative % |
|---|---|---:|---:|
| **Phase 1** | spacing `1.5`, colors `red-*`, radius `rounded-md` | 939 | 45% |
| **Phase 2** | spacing `2.5`/`5`, colors `indigo`/`sky`/`green`, radius `rounded-2xl`, shadow default | 892 | 88% |
| **Phase 3** | all remaining deprecated | 254 | 100% |

---

## 3) Enforcement Plan

### 3.1 Status Rules

| Status | Existing code | New code | New usages in existing files |
|---|---|---|---|
| **Allowed** | Keep | Required | Required |
| **Legacy** | Keep | **Forbidden** | **Forbidden** |
| **Deprecated** | Keep until migrated | **Forbidden** | **Forbidden** |

Key rule: **Legacy is not a free pass.** Legacy tokens may remain in untouched files, but any file edit must not add new Legacy or Deprecated usages.

### 3.2 Enforcement Mechanisms

| Mechanism | What it blocks | When | Status |
|---|---|---|---|
| **PR review checklist** | Deprecated + new Legacy in changed files | Immediately at lock | ✅ `.github/pull_request_template.md` |
| **CI grep check** | Deprecated tokens in diff (new lines) | At lock | ✅ `hostflow-frontend/scripts/check-foundation-tokens.sh` |
| **CI grep check (full)** | All Deprecated tokens in codebase | Phase 3 complete | ✅ `npm run foundation:scan` (non-blocking) |
| **Semantic color aliases** | Raw palette refs in new code | Post-lock sprint | ⬜ Not implemented |
| **ESLint custom rule** | Deprecated/Legacy in new files | Optional, Phase 2 | ⬜ Not planned (shell+diff sufficient) |

### 3.3 What Blocks Immediately at Lock

These are **forbidden in all new code** from day one:

**Spacing:** `1.5`, `2.5`, `3.5`, `5`, `7`, `16`, `20`, `24`, `32`, `96`

**Typography:** `text-4xl`, `text-6xl`, `leading-snug`, `leading-4`, `leading-5`, `leading-6`

**Colors:** `gray`, `green`, `teal`, `red`, `yellow`, `orange`, `sky`, `indigo`, `violet`, `purple`, `cyan`

**Radius:** `rounded-md`, `rounded-2xl`

**Shadow:** `shadow` (default), `shadow-lg`, `shadow-2xl`, `shadow-inner`

**Breakpoints:** `2xl:`

### 3.4 What Remains Temporarily Allowed

**Legacy (existing only, no new uses):**

| Category | Tokens |
|---|---|
| Spacing | `10`, `12` |
| Typography | `text-3xl`, `text-base`, `font-bold`, `font-normal`, `leading-none`, `font-mono` |
| Radius | `rounded-full`, `rounded-none` |
| Shadow | `shadow-none` |
| Z-index | `z-10`, `z-30`, `z-40` |
| Breakpoints | `xl:` |

### 3.5 CI Check (Implemented)

```bash
# Blocking (PR CI + local before push) — ratchet on the change range
cd hostflow-frontend && npm run foundation:check

# Non-blocking backlog report — migration debt, not a merge gate
cd hostflow-frontend && npm run foundation:scan
```

Workflow: `.github/workflows/frontend-static-qa.yml` (step: Foundation tokens).

#### Comparison-base contract (ratchet)

`foundation:check` answers: **did this change introduce new deprecated tokens?** It does **not** re-litigate already-accepted backlog. Mixing those two is how a promote-to-`main` PR goes red on tokens that already passed the gate at integration entry.

That failure is a **ratchet base mismatch** (wrong comparison base for the event), not “token-drift”. Tokens did not drift; the checker compared the change against a ref it did not come from.

| Event | Comparison | Notes |
|---|---|---|
| PR into `integration` (and any non-promote PR) | `merge-base(origin/<base>, HEAD)..HEAD` (`git diff origin/<base>...HEAD`) | Only the PR payload |
| Push to `integration` or `main` | `github.event.before`..`github.event.after` | Squash/merge = previous tip vs new tip |
| First push of a ref (`before` is the all-zero SHA) | `merge-base(origin/integration/release-product-a-b, tip)..tip` | Not `HEAD~1` (false green) and not `main` (false red) |
| Force-push | same `before`..`after`; unresolved `before` → **fail-closed** | Never skip; never fall back to `main` |
| Promote PR `integration/release-product-a-b` → `main` (same repo) | **already-ratcheted** (skip) | Promotion of code that already passed the ratchet at integration entry |
| Missing payload / unresolvable range | **fail-closed** | `--admin` stays an emergency tool, not the promote path |
| `foundation:scan` | full `src/` | Non-blocking migration debt |

Local (no CI event): `merge-base(origin/integration/release-product-a-b, HEAD)..HEAD`. Explicit `FOUNDATION_DIFF_BASE` overrides the contract (escape hatch, including forcing a check on a promote PR).

Do **not** default `FOUNDATION_DIFF_BASE` to `origin/main`. That is the mismatch.

Migration of the ~2000 deprecated uses remains a separate Foundation phase. Do not “fix” backlog tokens to make a promote PR green.

---

## 4) Success Metrics

### 4.1 Primary Targets (Deprecated → 0)

| Metric | Baseline | Target | Done when |
|---|---:|---:|---|
| Deprecated spacing uses | 834 | **0** | No `1.5`/`2.5`/`5`/etc. in src |
| Deprecated color uses | 655 | **0** | No `red`/`green`/`gray`/etc. families in src |
| Deprecated typography uses | 47 | **0** | No `leading-snug`/`text-4xl`/etc. in src |
| Deprecated radius uses | 426 | **0** | No `rounded-md`/`rounded-2xl` in src |
| Deprecated shadow uses | 123 | **0** | No default `shadow`/`shadow-lg`/etc. in src |
| **Total deprecated** | **2085** | **0** | Full migration complete |

### 4.2 Secondary Targets (Legacy freeze)

| Metric | Baseline | Target | Done when |
|---|---:|---:|---|
| New Legacy usages in PRs | unmeasured | **0** | CI blocks new Legacy in diffs |
| Legacy spacing uses | 36 | ≤36 (decreasing) | No increase from baseline |
| Legacy typography uses | 238 | ≤238 (decreasing) | No increase from baseline |

Legacy targets are **non-increasing**, not zero. Legacy debt is paid down opportunistically, not by big-bang migration.

### 4.3 Enforcement Targets

| Metric | Target | Done when |
|---|---|---|
| CI check active | Blocks Deprecated in the **event change range** | ✅ `npm run foundation:check` in `frontend-static-qa.yml` |
| PR checklist adopted | Reviewers check foundation tokens | ✅ PR template |
| Semantic color aliases | Config layer exists | `tailwind.config.cjs` updated |
| Re-scan delta | Deprecated count decreases each sprint | Tracked in sprint review |

### 4.4 Milestone Gates

| Milestone | Condition | Unlocks |
|---|---|---|
| **Lock** | Enforcement plan approved; CI check ready | `FOUNDATION_V1` (non-draft) |
| **Phase 1 complete** | Deprecated ≤1146 (45% reduction) | PRIMITIVES_V1_DRAFT |
| **Phase 2 complete** | Deprecated ≤254 (88% reduction) | Aggressive Legacy cleanup |
| **Migration complete** | Deprecated = 0 | Layer 2 full enforcement |

---

## 5) Governance Sequence

Correct order before `FOUNDATION_V1` lock:

| Step | Artifact / Action | Status |
|---|---|---|
| 1 | `FOUNDATION_AUDIT.md` | ✅ |
| 2 | `FOUNDATION_TOKEN_INVENTORY.md` | ✅ |
| 3 | `FOUNDATION_BENCHMARK.md` | ✅ |
| 4 | `FOUNDATION_V1_DRAFT.md` | ✅ |
| 5 | `FOUNDATION_ENFORCEMENT_AND_MIGRATION_PLAN.md` | ✅ This document |
| 6 | Implement CI check script | ✅ |
| 7 | Governance approval | ✅ 2026-05-29 |
| 8 | `FOUNDATION_V1` lock | ✅ |
| 9 | `PRIMITIVES_V1_DRAFT` | ← Next (Layer 2) |

**Do not lock `FOUNDATION_V1` before governance approval (step 7).**

---

## 7) Lock Readiness Checklist

Verified before `FOUNDATION_V1` lock:

| Check | Status | Detail |
|---|---|---|
| `foundation-allow` requires reason | ✅ | Format: `foundation-allow: <reason>` (min 8 chars). Bare marker does not suppress. Enforced in diff CI. |
| `--scan` stays non-blocking | ✅ | Not in CI or `qa:static`. Always `exit 0`. Backlog only. |
| Comparison-base contract | ✅ | PR vs merge-base(base, HEAD); push vs before..after; promote integration→main already-ratcheted; no `main` fallback; unresolved range fail-closed. Override: `FOUNDATION_DIFF_BASE`. |

**Lock candidate:** enforcement is active; legacy backlog does not block features.

---

## 8) Risk If Skipped

Without this plan, `FOUNDATION_V1` becomes a declaration:

- 2085 deprecated uses continue unchecked,
- new code adds more `red-*`, `rounded-md`, `spacing-1.5`,
- semantic color model never reaches `tailwind.config.cjs`,
- Layer 2 (Primitives) inherits the same drift.

The reference layer is ready. The enforcement layer is what makes it real.
