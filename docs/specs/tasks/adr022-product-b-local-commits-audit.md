# ADR-022 / Product B — audit of 6 unpushed local commits

**Date:** 2026-07-20  
**Base for any future port:** `c5be9375` (`integration/release-product-a-b`)  
**Historical source (do not rebase):** `feat/adr022-intake-policy-phase1-backend` @ `21ab01c1`  
**Upstream of that branch:** `origin/feat/adr022-intake-policy-phase1-backend` @ `a9c7e8e4` (local **ahead 6**, never pushed)  
**Merge-base with integration:** `0781f977` (integration is **176 commits** ahead of that base)

**Normative filters:** L0 · INV-16 (Decision Priority) · Flights R3.5 · ADR-021/022 · INV-17 (Communication Pipeline — already restored on integration)

**Next stage (not “audit”):** [`adr022-phase2-kickoff.md`](adr022-phase2-kickoff.md) — implement on current architecture spine; historical commits = requirements only.  
**Repo process:** [`../../governance/repository-operational-canon.md`](../../governance/repository-operational-canon.md)

---

## Executive verdict

| Commit | Class | One-line |
|--------|-------|----------|
| `d7c41aef` | **Discard** (as-is) | Closes G-B-05 in a doc file that no longer exists on integration |
| `b34aaa4a` | **Redesign → port docs** | F3-B-10 v1 Flow Spec — product intent valuable; must align with ADR-022 + Flights |
| `fc15643c` | **Redesign → port docs** | Card / Capability-first UX rules — keep intent, rewrite against current canon |
| `7dac9ada` | **Redesign** | Capability wizard UI — do **not** cherry-pick; splits Sales vs Recruitment ownership |
| `08a766ea` | **Redesign → port docs** | Usage / destination / convert contract — core Product B semantics |
| `21ab01c1` | **Port selective + redesign** | Convert mapping + ambiguous-match review + traceability UI |

**Do not** rebase or merge `feat/adr022-intake-policy-phase1-backend` onto integration.

**Do** open thin PRs from `c5be9375` after redesign, in this order:

1. Docs: F3-B-10 (Sales-only Capability) aligned to ADR-022  
2. Backend: convert mapping + ambiguous public match → SalesInquiry-facing review signal  
3. Frontend: Sales questionnaire create card (Sales Capability only)  
4. Frontend: inquiry↔questionnaire↔client traceability (SalesInquiry paths, not Lead CRM fallback as SoT)

---

## Per-commit analysis

### 1. `d7c41aef` — docs: close G-B-05 after staging walkthrough

| Axis | Finding |
|------|---------|
| **Business capability** | Records staging PASS for targeted-advertising Entity Profile auto-seed / repair / Product B send-submit |
| **Module ownership** | Ops/docs only — no runtime objects |
| **L0 / INV-16 / Flights** | N/A for code; doc target path is obsolete |
| **Lead/Application flow** | N/A |
| **Equivalent on integration** | `docs/specs/release-revenue-flow-audit.md` is **absent** on `c5be9375`. G-B-05 repair landed earlier via other merges (`feat/g-b-05-repair-hardening`, provisioning auto-seed). ADR-022 Phase 1 tests already cover match_or_create / attach on integration |
| **Class** | **Discard** as a patch. If a revenue-flow register returns, re-state G-B-05 status from current staging evidence — do not revive the deleted file solely to carry this commit |

---

### 2. `b34aaa4a` — docs: add F3-B-10 Flow Spec + register G-B-07

| Axis | Finding |
|------|---------|
| **Business capability** | Manager creates a questionnaire by choosing a **Capability** (direction), not by touching Entity Profile / platform knobs |
| **Module ownership** | Spec correctly says answers land in **Sales inquiries** for B2B; Capability bundle maps to Form Definition persistence |
| **L0 / INV-16 / Flights** | Spec is Forms → (implicit) Sales. Must explicitly require **Forms → Flights → Sales intake adapter** for destination; must not invent Sales↔Recruitment shortcuts |
| **Lead/Application flow** | Uses Application/Sales Inquiry language in later revisions; v1 still speaks TenantLeadForm as persistence (acceptable as ADR-021 facade) |
| **Equivalent on integration** | **No** `F3-B-10-create-questionnaire-flow-spec.md` on integration |
| **Class** | **Redesign → port docs.** Keep Capability-first mental model; rewrite against ADR-022 axes (Purpose / Target Profile / Submission Policy) and Flights ownership |

---

### 3. `fc15643c` — docs: questionnaire card + Capability-first UX

| Axis | Finding |
|------|---------|
| **Business capability** | Create flow **ends at a working tool** (post-save card: send / copy / preview), not at Save |
| **Module ownership** | Card actions must call **Sales** send path (now Communication Pipeline / PR #81 binder), not raw transport |
| **L0 / INV-16** | “No platform jargon in walkthrough” is compatible with INV-16 (UI must not invent ownership) |
| **Equivalent on integration** | Missing with F3-B-10 |
| **Class** | **Redesign → port docs** (fold into rewritten F3-B-10) |

---

### 4. `7dac9ada` — feat: Capability-first create + post-save card (code)

| Axis | Finding |
|------|---------|
| **Business capability** | Admin UI: pick Capability → auto-load preset → save → QuestionnaireCard |
| **Objects introduced** | `CreateQuestionnaireWizard`, `QuestionnaireCard`, `QuestionnaireQualityIndicator`, `intakeCapabilities`, `questionnaireQuality`; heavy edits to `LeadFormsSettingsPage` / `IntakeFormDetailPage` |
| **Module ownership** | **Problem:** `INTAKE_CAPABILITY_CATALOG` hard-codes **both** `service_sales.targeted_advertising` **and** `recruitment.candidate.driver_ce` in one Sales-leaning admin create path. That mixes independent modules in one product noun without Flights destination separation |
| **L0 / INV-16** | **Fail if cherry-picked as-is.** Capability catalog for Recruitment hiring must not be owned by the Sales questionnaire create surface. Platform Form Definition create is OK; **cross-domain Capability menu is not** |
| **Lead/Application flow** | Navigates to `settingsLeadFormDetailPath` (Lead Forms settings). Acceptable as Forms Platform shell; must not treat Lead Forms list as Sales SoT |
| **Flights** | No Flights / destination_contract usage in wizard — destination implied by Entity Profile code only |
| **Equivalent on integration** | All new UI files **missing**; Lead Forms settings exist without Capability-first entry |
| **Class** | **Redesign.** Port **Sales-only** Capability (`targeted_advertising`) + card UX on a fresh branch. Recruitment Capability belongs to a Recruitment-owned create path (or shared catalog service with module-scoped filters), not this wizard |

---

### 5. `08a766ea` — docs: F3-B-10 rev 4 usage / destination / convert

| Axis | Finding |
|------|---------|
| **Business capability** | Usage modes (invite from inquiry vs public link), compatibility rules, submission routing, convert mapping table, G-B-08 gap |
| **Module ownership** | Explicitly: module owner Sales / `client_lead`; personal invite attaches to **same** Sales Inquiry; public match_or_create attaches or creates inquiry |
| **L0 / INV-16 / Flights** | Aligns with ADR-022 Phase 1 (Sales Inquiry only matching) **if** routing goes Forms → Flights → Sales adapter. Doc must forbid matching ClientAccount/Candidate at submit (already ADR-022) |
| **Lead/Application flow** | Correctly treats Lead as transport facade for Sales Inquiry (ADR-021 Phase 1) |
| **Equivalent on integration** | ADR-022 Phase 1 **runtime** + tests exist (`test_adr022_intake_policy_phase1.py`). This **product Flow Spec** does not |
| **Class** | **Redesign → port docs.** Highest-value doc content of the six; rewrite onto integration canon (cite ADR-022, Flights R3.5, Communication Pipeline for send) |

---

### 6. `21ab01c1` — feat: usage copy, convert mapping, inquiry traceability

| Axis | Finding |
|------|---------|
| **Business capability** | (a) Card copy for invite vs public link; (b) ambiguous public match → manager review flag; (c) convert Lead→ClientAccount maps industry/budget/notes from questionnaire; (d) UI links inquiry ↔ form ↔ client |
| **Objects / ownership** | Backend: `intake_submit_service` (platform intake), `client_accounts/conversion` (Sales convert), `lead_questionnaire_invite` (Sales invite merge). Frontend: `InquiryTraceabilityPanel`, `inquiryTraceability` utils |
| **L0 / INV-16 / Flights** | Review flagging on **Lead.normalized / Lead.stage** is transport-layer. Prefer projecting review onto **SalesInquiry** (or opaque result) so Sales owns the signal; Lead remains facade |
| **Lead-centric risk** | `inquiryTraceability` falls back to `CRM_APP_PATHS.leads/:id` and reads `Lead` as primary type. After Sales Inquiry workspace (PR #81/#83), SoT paths should be **SalesInquiry** routes; Lead paths only as legacy bridge |
| **Equivalent on integration** | Invite merge already stores `sales_questionnaire` + basic need summary — **without** industry/budget/timeline/notes enrichment from tip. **No** `_mark_inquiry_requires_manual_review`. **No** conversion `source_form_id` / questionnaire field mapping. **No** traceability panel |
| **Class** | **Port selective + redesign:** |
| | • **Port** convert mapping + invite need enrichment (Sales-owned) |
| | • **Redesign** ambiguous-match review to SalesInquiry-facing signal (not `lead.stage = review_required` as long-term SoT) |
| | • **Redesign** traceability UI onto SalesInquiry / client-acquisition paths |
| | • Card usage copy: port with QuestionnaireCard redesign (commit 4) |

---

## Cross-cutting checks

### Already on integration (do not re-implement)

- ADR-022 Phase 1 `match_or_create` / `attach` + tests  
- Targeted-advertising form seed / repair (G-B-05 lineage)  
- Sales questionnaire invite + Communication Pipeline binder (PR #81)  
- SalesInquiry duplicates / rematch stub (PR #83)  
- Module deployHosts / CSRF integrity (PR #82/#84)

### Must not return

- Single admin wizard that creates **Recruitment** and **Sales** Capabilities without module-scoped ownership  
- Public submit matching **ClientAccount** / Candidate directly  
- Send/email bypass of Communication Pipeline  
- Treating `Lead` CRM detail as the long-term Sales workspace SoT  
- Dropping stash Alembic drafts from recovery into live chain (already classified elsewhere)

### Recommended new branch names (from `c5be9375`)

```text
docs/f3-b-10-sales-capability-flow          # rewritten Flow Spec
feat/sales-questionnaire-convert-mapping    # conversion + invite enrichment
feat/sales-ambiguous-match-review           # review signal on Sales result
feat/sales-capability-create-card           # Sales-only wizard + card
feat/sales-inquiry-traceability-ui          # panel + paths
```

Keep `feat/adr022-intake-policy-phase1-backend` checked out nowhere; retain as **read-only historical source** until those PRs land, then delete local branch (remote already lacks the 6 commits).

---

## Suggested implementation order

1. **Docs PR** — F3-B-10 Sales-only, ADR-022 + Flights + Pipeline citations.  
2. **Convert mapping PR** — low coupling, clear Sales ownership.  
3. **Ambiguous-match review PR** — design SalesInquiry field/projection first.  
4. **Create-card PR** — Sales Capability only.  
5. **Traceability UI PR** — depends on stable SalesInquiry routes.

Stop after each PR for INV-16 / ownership review before the next.
