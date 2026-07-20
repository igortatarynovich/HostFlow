# Sales → Communication — sequential product queue (locked)

**Status:** **NORMATIVE QUEUE** (one active product slice at a time)  
**Date:** 2026-07-20  
**Trusted base:** `integration/release-product-a-b` @ `e276e81f`+ (fast-forward only)  
**Parents:** [Pipeline v1 seal](../architecture/sales-domain-pipeline-v1.md) · [Creation Origins v1](../architecture/client-account-creation-origins-v1.md) · [Phase 2 kickoff](adr022-phase2-kickoff.md) · [Repository Operational Canon](../../governance/repository-operational-canon.md)

> Sales domain contracts are sealed (PR #93 / #94). Product wiring is **not** finished.  
> Communication is **in the queue**, but **no Communication product branch** runs until Sales Stages 1–3 are closed.  
> **Supersedes** Origins §9 implementation order and kickoff “Capability UI last” naming where they conflict.

---

## 1. Frozen completed state

| Stage | Status |
|-------|--------|
| Sales Domain Pipeline v1 seal | ✅ PR #93 |
| ClientAccount Creation Origins v1 | ✅ PR #94 |
| Convert Mapping | ✅ |
| Ambiguous Match Review | ✅ |
| Sales Inquiry Traceability | ✅ |
| Repository Health | ✅ required PASS before each new branch |

**Still open (product, not domain invent):**

- Sales UI still Lead-centric in places  
- Old Lead convert may bypass Review  
- `match_existing` not fully applied on Convert  
- Manual ClientAccount create is contract-only  
- Outbound communications may create unbound threads  
- Signatures lack a single Communication policy  

---

## 2. Locked sequence (no parallel product branches)

| # | Stage | Branch | Scope (thin) |
|---|-------|--------|--------------|
| **1** | Capability UI | `feat/sales-capability-ui` | Display-only: Capability, Review status, Convert availability / result, Traceability. UI does **not** compute or decide domain outcomes. |
| **2** | Manual ClientAccount creation | `feat/manual-client-account-creation` | Backend `create_client_account_manually`; `origin_type=manual_creation`; no fake Lead/SI/Flights/Convert/ad provenance. UI may follow in a later thin PR. |
| **3** | Sales Pipeline product wiring | `fix/sales-pipeline-v1-product-wiring` | Close Pipeline v1 §3 GAPs: Review gate on product convert; apply `match_existing`; SalesInquiry SoT in workspace; all SI→ClientAccount via Convert Mapping; manual path only `manual_creation`; block or rewire uncontrolled creates. |
| **4** | Outbound context binding | `feat/communication-outbound-context-binding` | Outbound always entity-bound before provider; SalesInquiry → Thread link for questionnaire email; fail-closed; G13 links SoT; G14 ClientAccount link on Convert (no migrate/delete of old SI link). |
| **5** | Signature model and policy | `feat/communication-signature-policy` | Signatures owned by Communication; purpose-driven selection; immutable snapshot on send; Settings → Communications → Signatures. |
| **6** | Composer UX | `feat/communication-composer-context-signature` | Thin UX: show thread binding + active signature; allow signature swap; block send if context lost; no “Без привязки” for Sales outbound. |
| **7** | Communication integrity | `fix/communication-context-integrity` | Repair historical unbound outbound only with unambiguous provenance; ambiguous → review queue; permanent gate: new outbound without entity link impossible. |
| **8** | Next CRM | *(later)* | Service Orders / quotes / deals |

---

## 3. Stage 1 — Capability UI ✅

**Branch:** `feat/sales-capability-ui` (merged PR #96)  
Display-only spine: Capability proxy, Review status, Convert availability/result, Traceability.

---

## 3b. Stage 2 — Manual ClientAccount creation ✅

**Branch:** `feat/manual-client-account-creation` (merged PR #97)  
**Task:** [stage-2-manual-client-account-creation.md](stage-2-manual-client-account-creation.md)

---

## 3c. Stage 3 — Sales Pipeline product wiring

**Branch:** `fix/sales-pipeline-v1-product-wiring` (merged)  
**Task:** [stage-3-sales-pipeline-product-wiring.md](stage-3-sales-pipeline-product-wiring.md)  
**Slice 1 done:** product convert → `convert_sales_inquiry_mapping`; Review SoT; mandatory convert audit; idempotent replay.

## 3d. Stage 3 — Convert entrypoints (current)

**Branch:** `fix/sales-pipeline-v1-convert-entrypoints`  
**Task:** [stage-3-sales-pipeline-convert-entrypoints.md](stage-3-sales-pipeline-convert-entrypoints.md)  
**Allowed (slice 2):** Lead `convert-client` → compatibility wrapper over mapping; FE → `convertSalesInquiryToClient`; dual-entrypoint contract tests; staging/intake readiness for Review+Flights.  
**Forbidden in this slice:** Communication; entity-profile outcomes; inventing a second convert engine; deleting Lead HTTP route.

---

## 4. Stage 4 — Communication Outbound Context Binding (queued)

**Invariant:** every HostFlow outbound message is bound to a canonical entity **before** send.

```text
Entity → Communication Context → Thread Entity Link → Message Outbox → Provider
```

Sales questionnaire email:

```text
SalesInquiry → Thread↔SalesInquiry → Email
```

**Not allowed:** Email → unbound Thread → operator searches for inquiry.

Rules (summary): outbound thread without entity link forbidden; no provider handoff without link; G13 `communication_thread_entity_links` sole link mechanism; Convert adds G14 ClientAccount link without moving/deleting SI link; inbound unknown may stay unbound; outbound never.

---

## 5. Stage 5 — Signature policy (queued)

Signatures belong to **Communication**, not Sales/Recruitment. Modules pass **purpose** only (e.g. `sales_outreach`, `recruitment_candidate`, `billing_notice`, `service_order_update`).

Priority: explicit message choice → purpose assignment → user default → company default → none only if policy allows. Persist immutable signature snapshot on the message.

Settings: **Настройки → Коммуникации → Подписи**.

---

## 6. Development rule

Exactly **one** product slice active.

Next branch only after:

1. Current PR merged  
2. Fast-forward `integration/release-product-a-b`  
3. `make repo-health` **PASSED**  
4. Stale worktrees pruned / checked  
5. One dedicated worktree (create or reuse)  

**Do not** open Communication product branches while Stages 1–3 are open.

---

## 7. History

- 2026-07-20: Queue locked — Capability UI → Manual create → Pipeline wiring → Communication (4–7) → CRM. Supersedes Origins §9 order and kickoff “Capability after Origins only” where conflicting.
