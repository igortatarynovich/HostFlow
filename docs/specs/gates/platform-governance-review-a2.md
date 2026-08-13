# A2 — Platform Governance Review

**Status:** **PASS_WITH_CONSTRAINTS** (2026-08-03)  
**Decision ID:** `PLATFORM_GOVERNANCE_A2_PASS_WITH_CONSTRAINTS`  
**Type:** Cross-platform L0/operating gate (not a product feature)  
**Parents:** [Platform Completion Roadmap § A2](../architecture/platform-completion-roadmap.md) · [Epic C Complete Gate](epic-c-complete-gate.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md)  
**Base:** stacked on Epic C Complete Gate (`docs/epic-c-complete-gate` / PR #220)

> Verify the **boundary principle** after Epic C growth: platforms stay independent;  
> modules integrate only via public contracts/adapters.  
> This is **not** a re-test of Communication wiring (that closed at the Epic C Complete Gate).

---

## Formal decision

| Field | Value |
|-------|-------|
| **Outcome** | `PASS_WITH_CONSTRAINTS` |
| **Date** | 2026-08-03 |
| **Result** | Platforms stable enough for **Phase B** (Meta Intake + Stage 3) |
| **Next Product Track** | **Meta Intake Completeness** → Stage 3 slice 3–4 |
| **Not outcome** | Clean `PASS` (Catalog Notifications≠Communication; legacy SMTP; Entity Workspace not yet SoT) · `STOP` (no second Communication pipeline; boundaries hold) |

**Rationale:** Communication is Epic C — complete (`PASS_WITH_CONSTRAINTS`). Acquisition / Forms / Documents each have identifiable SoTs. Residual gaps are owned constraints or sequenced later phases — not silent boundary violations. Phase B may open.

---

## Checklist

| # | Theme | Status | Evidence (one line) |
|---|--------|--------|---------------------|
| 1 | One SoT per platform (Acquisition, Communication, Documents, Forms, Entity, Automation) | **PASS_WITH_CONSTRAINTS** | Communication `backend/app/communications/`; Acquisition ADR-024 + intake; Forms ADR-007 + `forms_platform`; Documents Hub + REF-4 baseline; Entity Workspace = Phase D (not invented); dual Automation planes documented (A2-F5) |
| 2 | Remaining legacy contracts mapped or removed | **PASS_WITH_CONSTRAINTS** | [c0-1b map](../tasks/c0-1b-legacy-writers-migration-map.md) + [c0-3 map](../tasks/c0-3-legacy-delivery-migration-map.md); SMTP allowlist frozen (`test_legacy_bypass_allowlist_does_not_grow`); non-empty = Epic C R2 |
| 3 | No duplicate domain models / parallel writers | **PASS_WITH_CONSTRAINTS** | No second outbound pipeline (INV-17 + C2 AST); residual SMTP writers (R2); Acquisition Campaign ≠ Communication Campaign; Catalog Notifications vs Communication delivery Owns = R5/RFC |
| 4 | ADR + Canon + Catalog + AGENTS aligned | **PASS_WITH_CONSTRAINTS** | Queue/roadmap/maturity/AGENTS aligned on this PR; **Catalog Index has no Communication capability** (Notifications only) → Architecture RFC (A2-F1) — not rewritten here |
| 5 | Legacy migration map current | **PASS** | Map matches `_SMTP_ALLOWLIST`; migrated lead paths marked; minor removal-plan hygiene optional |

### Epic C residuals (disposition)

| ID | Residual | A2 disposition |
|----|----------|----------------|
| **R1** | C2.4 Scheduling frozen | **Accepted** — do not unfreeze on A2 |
| **R2** | Legacy SMTP allowlist non-empty | **Deferred** Engineering / Phase B burn-down; map must not grow |
| **R3** | Platform lazy-imports of module adapters | **Accepted** — published adapters only; optional registration invert later |
| **R4** | Campaign/Automation publish soft on Intent Registry | **Engineering follow-up** — before new Intent consumers |
| **R5** | Catalog Notifications vs Communication naming | **Architecture RFC required** (L0) — see below; not an A2 apply-pass |

---

## Findings

| ID | Finding | Sev | Owner | Disposition |
|----|---------|-----|-------|-------------|
| **A2-F1** | Catalog / Manifest / L0 pyramid have no **Communication** capability; Notifications passport still Owns delivery channels | High (L0 docs) | Architecture Canon | **Architecture RFC** (separate PR). Record constraint here only |
| **A2-F2** | Legacy SMTP allowlist still non-empty (Epic C R2) | Medium | Communication + modules | Deferred burn-down |
| **A2-F3** | `policy_gate` / `manual_thread_reply` lazy-import module adapters (R3) | Low | Architecture / Communication | Accept; optional invert |
| **A2-F4** | Publish-time Intent Registry membership soft (R4) | Medium | Communication | Hardening PR before new intents |
| **A2-F5** | Dual automation: ADR-019 `AutomationRule` vs C2 `communication_*` automation | Medium (clarity) | Architecture + Communication | **Boundary note:** Communication Automations = Intent emitters under Communication; Platform Automations = cross-entity control plane. No merge in A2 |
| **A2-F6** | Forms maturity matrix vs module-scope Sprint 1–6 complete | Medium (docs) | Architecture / Forms | Clarified in maturity notes this PR — Phase C Forms Platform (Passport/Manifest/Runtime) still open |
| **A2-F7** | Entity Workspace not yet a platform SoT | Baseline | Product Architecture | Phase D; do not invent SoT |
| **A2-F8** | Documents Foundation still consolidating | Medium | Documents | Phase E expected; does not block Meta/Stage 3 |
| **A2-F9** | C2.4 Scheduling frozen (R1) | Accepted | Communication Product | Explicit unfreeze required |

---

## R5 — Notifications → Communication (RFC, not A2 rewrite)

`platform-capability-catalog.md` is **L0 FROZEN**. Renaming or splitting Notifications ↔ Communication changes Passport Owns / Requires / Manifest ownership → **Architecture RFC** (or `l0-errata`), not a drive-by Catalog edit in this gate.

**Allowed here:** record the constraint; point Product Track to Phase B; leave Catalog/Manifest/L0 pyramid unchanged.

**RFC follow-up (Engineering / Architecture):** add Communication passport (or rename) and narrow Notifications to in-app Activity (ADR-012) vs delivery owned by Communication.

---

## Relation to Epic C Complete Gate

| Gate | Question answered |
|------|-------------------|
| Epic C Complete | Is Communication one platform capability? |
| **A2 (this)** | Did platform growth violate cross-platform boundaries? |

A2 does **not** re-run C0–C2 checklists. Communication residuals R1–R5 remain owned; A2 only dispositions them for Phase B readiness.

---

## Ordered follow-ups

### Product Track (next)

1. [Meta Intake Completeness](../tasks/meta-intake-completeness.md) ✅ [#222](https://github.com/igortatarynovich/HostFlow/pull/222)  
2. Stage 3 slice 3 — SalesInquiry product flow ✅ [#224](https://github.com/igortatarynovich/HostFlow/pull/224)  
3. Stage 3 slice 4 — [hard module separation](../tasks/stage-3-slice-4-hard-module-separation.md)  
4. Then: Forms Platform → Entity Workspace → Documents → Billing → AI  

### Engineering / Architecture (non-blocking for Meta start)

| Order | Item | Blocks Meta/Stage 3? |
|-------|------|----------------------|
| E1 | Architecture RFC: Notifications ↔ Communication (A2-F1 / R5) | Soft — Catalog docs only |
| E2 | R4 Intent Registry publish membership | Recommended before new intents |
| E3 | R2 SMTP allowlist shrink | No |
| E4 | R3 adapter registration invert | No |
| E5 | Do not start C2.4 until explicit unfreeze | — |

---

## Suggested branch

`docs/platform-governance-review-post-epic-c`

## DoD

- [x] Written review checklist + findings + ordered follow-ups  
- [x] Epic C residuals R1–R5 dispositioned  
- [x] R5 marked Architecture RFC (Catalog not rewritten)  
- [x] Status docs point Product Track at Phase B (Meta → Stage 3)  
- [x] No drive-by runtime refactors  
