# Acquisition UI Cutover C-4 — Test submission & field discovery

**Status:** **DONE** — operator smoke PASS 2026-07-26  
**Date:** 2026-07-24  
**Canon:** [acquisition-ui-cutover.md](acquisition-ui-cutover.md) (C-4 row + onboarding lifecycle)  
**Parents:** ADR-024 · C-3 Sources foundation (#160) · [sales-to-comms-sequential-queue.md](sales-to-comms-sequential-queue.md)  
**Next:** [C-7 Подборы decommission](acquisition-ui-cutover-c7-searches-decommission.md) — **ACTIVE Product Track**  
**Blocks:** Stage 5 PR-2 remains paused until cutover C-7 PASS

> C-4 closes the **Test Lead → Field Discovery** step of Source onboarding.  
> Operator obtains a **sample submission**, sees **detected fields + masked samples**, and can **dry-run normalize** — **without** creating production Candidate / Application / Sales Inquiry by default.  
> **Not** the Mapping workspace (C-5). **Not** Source Diagnostics ops console (post–C-7).

---

## 1. Why now

C-3 delivered Marketing → Sources inventory + Mapping Health summary, but **Test lead** still deep-links into Settings Meta debug (`build_source_paths` comment: “C-4 will own real test-lead UX”).

Without C-4, connecting a new Meta (or other) source still requires an engineer / Settings-admin path to understand real provider fields. That is exactly the onboarding gap cutover names.

```text
Connect → Source → [C-4 Test Lead + Discovery] → [C-5 Mapping] → Destination → Flight → First Lead
```

---

## 2. Product job (one sentence)

From a Source row, a non-developer operator can **get a sample payload**, **inspect raw + discovered fields (PII masked)**, and **see a dry-run normalization** — then hand off to C-5 to confirm mapping.

---

## 3. Locked boundary vs C-5 / Diagnostics

| Concern | C-4 | C-5 | Diagnostics (post–C-7) |
|---------|-----|-----|-------------------------|
| Obtain sample (test / capture-next / paste) | ✅ | — | — |
| Raw payload inspector (masked) | ✅ | may deep-link sample | full ops timeline |
| Field discovery table | ✅ proposals | ✅ editable decisions | drift alerts on live leads |
| Persist `mapping_rules` / versioning | ❌ | ✅ | — |
| Routing preview (entity / vacancy / queue / duplicate) | ❌ (stub CTA only) | ✅ | explain one live lead |
| Create Candidate / Application / Inquiry | ❌ default | ❌ unless explicit opt-in later | replay tools |
| New mapping engine | ❌ | ❌ | ❌ |

**Rule:** C-4 may **propose** HostFlow targets and run **preview-only** normalize. It must **not** become a second place that saves mapping or invents routing SoT.

---

## 4. Test-lead modes (product)

| Mode | Priority | Behavior |
|------|----------|----------|
| **A — Official Meta test lead** | Primary (Meta Sources) | Operator follows in-product instruction (or available Meta test workflow). HostFlow **captures** the resulting raw payload for **this Source**, seeds discovery sample. |
| **B — Capture next real lead as sample** | Secondary | Next matching submission processes under normal ingest **and** is tagged/stored as mapping sample for this Source (UI shows masked values). |
| **C — Paste saved payload** | Admin / fallback only | Paste JSON → discovery + dry-run. **Not** the default CTA on Marketing Sources. |

Non-Meta Sources with an Intake Form binding: prefer existing HostFlow form sample / preview paths over inventing a Meta-only UX.

---

## 5. Default safety (non-negotiable)

1. **Dry-run normalize by default** — reuse preview semantics (`mapping/preview` / equivalent), **not** production funnel create.  
2. **No Candidate / Application / Sales Inquiry** from C-4 default path.  
3. Existing `mapping/test-ingest` (creates **Lead draft**) is **opt-in only** if exposed at all in C-4; label clearly as “draft Lead for mapping”, never as production convert. Prefer **omit** from Marketing C-4 UI and keep under Settings until C-5 decides.  
4. **Mask PII in UI** (phone/email/name samples) where feasible; raw inspector respects tenant `mask_pii_in_logs` / equivalent policy.  
5. Sample storage is **tenant-scoped**, tied to Source / IntakeSourceProfile (or Meta form id), never cross-tenant.

---

## 6. UX surface

### Entry

- Marketing → Sources → row action **Test lead**  
- Replace Settings deep-link (`?tab=debug`) with Marketing-native route, e.g.  
  `/app/marketing/sources/:sourceId/test-lead`  
  (exact path may follow existing SPA path manifest; must be Marketing IA, not Settings-only).

### Screen sections (minimum)

1. **Source context** — provider, page/form label, Mapping Health summary (read from C-3 projection).  
2. **Obtain sample** — Mode A primary; Mode B toggle; Mode C behind “Advanced”.  
3. **Raw payload inspector** — collapsible JSON; masked.  
4. **Field discovery table**

| Column | Content |
|--------|---------|
| Provider field | `source` key from sample (`extract_source_fields_from_sample` or Graph form fields ∪ sample) |
| Sample (masked) | First sample value, masked |
| Proposed HostFlow target | Best-effort proposal from existing rules / heuristics (read-only in C-4 if already mapped; else “Unmapped”) |
| Status | Mapped / Unmapped / New since last sample |
| Action | **Select in Mapping** → navigates to C-5 workspace (or Settings mapping path until C-5 ships) |

5. **Dry-run normalize** — button → show `normalized_payload` + mapping validation summary (accepted / rejected / missing). No side-effect write except optional sample persistence.  
6. **CTA** — **Continue to Mapping** (C-5). Do not claim “Ready” solely from discovery.

---

## 7. Reuse (no new mapping engine)

Must reuse, wrap, or thin-facade — **not** fork:

| Existing | Use in C-4 |
|----------|------------|
| `IntakeSourceProfile.mapping_rules` / Meta form `mapping_rules` | Read for “already mapped” + proposals |
| `extract_source_fields_from_sample` | Discover fields from sample |
| `POST …/intake-forms/{id}/mapping/preview` | Dry-run normalize for form-bound Sources |
| Meta admin incoming preview / Graph field preview | Seed Mode A/B samples for Meta (call existing services; do not rebuild Graph client) |
| C-3 `test_lead_path` / `build_source_paths` | Point to new Marketing test-lead route |

**Forbidden:** parallel mapping runtime, new field dictionary, silent drop of unknown fields in preview (unknown → visible Unmapped / Needs review signal).

---

## 8. Backend / API sketch (one PR preferred)

Keep surface small; prefer extending platform Marketing Sources, not Settings-only:

| Endpoint (illustrative) | Role |
|-------------------------|------|
| `GET /api/v1/platform/marketing/sources/{source_id}/sample` | Current sample + discovered fields (masked) + mapping status vs rules |
| `POST …/sample/capture-next` | Arm Mode B for this Source (expires; single-use or time-boxed) |
| `POST …/sample/from-payload` | Mode C — admin/manager only |
| `POST …/sample/preview` | Dry-run normalize using current (or proposed) rules — **no entity create** |
| Meta Mode A | Prefer: poll/attach latest test submission already ingested as Lead raw for this form/Source; document operator steps if Graph “send test lead” is external |

Exact paths may fold under existing Meta admin services with a Marketing façade — **contract matters more than URL**.

**Writes allowed in C-4:** sample blob / capture-next arm / last_discovered_fields metadata on Source profile  
(`publication_config_v1.mapping_discovery_v1` — policy resolver ignores unknown keys; no dedicated column in this PR).  
**Writes forbidden:** production Candidate/Application; Flight bindings; Campaign mutations; Mapping Health → Ready without C-5 confirm (Health may move to `needs_review` when new fields appear — OK).

---

## 9. Security

Extend / twin C-3 threat model for sample + preview surface:

| Risk | Mitigation |
|------|------------|
| PII in discovery UI | Mask samples; RBAC manager+; no public route |
| Cross-tenant sample | Always `tenant_id` from session + RLS |
| Preview as mutate | Preview endpoints must not create Candidate/Application; audit if draft Lead opt-in exists |
| Paste arbitrary JSON (Mode C) | Role-gate; size limit; no SSRF; treat as untrusted input to normalizer only |

Update `docs/security/threat-models/acquisition-marketing-sources.md` (or add C-4 section) in the same PR.

---

## 10. Acceptance (C-4 PASS)

- [ ] From Marketing → Sources, **Test lead** opens Marketing-native discovery UX (not Settings debug as the only path).  
- [ ] Mode **A** (Meta) and/or **B** documented and workable for at least one connected Meta Source in staging/smoke.  
- [ ] Operator sees **detected fields + masked samples** from a real or test payload.  
- [ ] **Raw payload inspector** available (masked per policy).  
- [ ] **Dry-run normalize** runs without creating Candidate / Application / Inquiry.  
- [ ] Unknown / new fields surface as Unmapped / Needs review — **not** silently omitted.  
- [ ] CTA to Mapping (C-5 or interim Settings mapping) works from discovery table.  
- [ ] Scoped tests: tenant isolation, mask behavior, preview no production side-effects, scan that Sources Test lead no longer **only** targets Settings debug.  
- [ ] `make docs-lint` green; cutover acceptance checkbox for C-4 checked when merged.

---

## 11. Explicit OUT

- Persisting full mapping decisions / versioning / routing preview → **C-5**  
- Form Builder under Marketing → **C-6**  
- Подборы decommission → **C-7**  
- Source Diagnostics ops console → post–C-7  
- FlightAdBinding / ingest resolver changes → runtime PR (#161 line), not C-4  
- Quote / Commercial Confirmation / Sales Readiness → ADR-020 Stage 1B+ (blocked by Epic C Gate + A2)  
- New mapping engine or local field dictionaries  

---

## 12. PR plan

**Single Product PR** preferred (UI + façade API + tests + threat-model note), unless sample persistence needs a migration — then:

1. **PR-1** — sample store + preview API + tests  
2. **PR-2** — Marketing test-lead UI + Sources CTA cutover + docs

Branch (proposed): `feat/acq-c4-test-lead-field-discovery`  
Base: `integration/release-product-a-b` (FF only; worktree per operational canon)

**Engineering Track:** full-repo pytest red remains base debt — do not block C-4 when scoped C-4 tests + qa-static / docs-lint are green (same exception class as C-2/C-3).

---

## 13. Handoff to C-5

C-4 PASS means the operator can answer: **“What fields does this Source actually send?”**  
C-5 starts when they must answer: **“Where does each field go, and what will routing do?”**

Do not expand C-4 to absorb C-5 because the discovery table already has an Action column.
