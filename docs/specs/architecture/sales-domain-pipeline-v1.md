# Sales Domain Pipeline v1 — architectural seal

**Status:** **DOMAIN CONTRACTS SEALED** · **PRODUCT WIRING GAPS OPEN**  
**Date:** 2026-07-20  
**Trusted base:** `integration/release-product-a-b` @ `23656b54`+  
**Kind:** L2 architecture seal (revision evidence — not a bug hunt)  
**Parents:** [Phase 2 Flow Spec](../workflows/adr022-phase2-sales-only-capability-flow.md) · [Convert mapping](../tasks/sales-questionnaire-convert-mapping.md) · [Ambiguous match review](../tasks/sales-ambiguous-match-review.md) · [Traceability](../tasks/sales-inquiry-traceability.md) · [ADR-020](ADR-020-sales-to-engagement-commercial-model.md) · [ADR-023](ADR-023-recruitment-sales-module-separation.md)  
**Next:** Capability UI (display-only) → `create_client_account_manually` implementation → product wiring closeout (Pipeline v1 §3)

> This document records the Phase 2 revision. It seals what the four domain slices **own** as a coherent Sales Domain Pipeline v1, and lists **open product gaps** that must not be papered over before Marketing → Intake → CRM Client is claimed end-to-end.

---

## 1. What is sealed

```text
Intake → Flights → SalesInquiry (SoT)
  → Capability (contract)
  → Review (SalesInquiry-owned)
  → Convert Mapping (no decisions)
  → Traceability (write-once)
  → ClientAccount (conversion origin)
```

| Stage | Owner | Implementation entry |
|-------|-------|----------------------|
| SalesInquiry SoT | Sales | `backend.app.models.sales_inquiry` |
| Flights destination / provenance | Flights | opaque ledger refs only in Sales |
| Capability | Sales | contract in Flow Spec (UI later) |
| Review | Sales | `ambiguous_match_review` |
| Convert | Sales | `convert_sales_inquiry_mapping` |
| Traceability | Sales | `sales_inquiry_traceability` / `record_lineage_after_convert` |

**Sealed claim:** the four Phase 2 domain slices form a **non-contradictory contract set** for the **inquiry → ClientAccount (conversion)** spine. Recruitment does not participate. Convert does not re-route. Traceability does not recompute.

**Not sealed:** live Sales HTTP/UI still keyed primarily by Lead transport; product convert may bypass Review. See §3.

---

## 2. Revision checklist

| # | Question | Verdict | Evidence |
|---|----------|---------|----------|
| 1 | No duplicated responsibility Convert / Review / Traceability | **AMEND** | Review owns match SoT (`ambiguous_match_review_v1`). Convert gates via `review_blocks_convert` (`convert_mapping.py`). Traceability snapshots review / does not rematch (`sales_inquiry_traceability.py`). **Amend:** Convert does not yet **apply** Review `match_existing` / `client_account_id` — it always goes through `convert_client_lead` create/idempotent-by-lead. |
| 2 | Lead as factual SoT? | **GAP** | Normative: Lead = transport facade (Flow Spec §3.5). Convert still **requires** `SalesInquiry.lead_id` (`convert_mapping.py`). Live Sales workspace / convert API still keys off Lead (`applications/mutations.py`, Sales Application workspace). Product SoT path ≠ SalesInquiry row. |
| 3 | State machine coverage | **AMEND** | Flow Spec §7 covers Flights → open / review-required → convert. Code also uses `received`, `reviewing`, `waiting_for_information`, review `not_required` / `cancelled`, stamp → `converted`. Capability “decided” is contract-only until Capability UI. Expand §7 (this seal §4) without inventing new behaviour. |
| 4 | Review bypass | **GAP** | Canonical path: `_assert_inquiry_convertible` → `review_blocks_convert`. Product path: `mutations.convert_sales_inquiry` → `convert_client_lead_to_client_endpoint` → `convert_client_lead` — **no** review gate. `convert_sales_inquiry_mapping` is domain/tests-first (no Sales HTTP mount yet). |
| 5 | ClientAccount create outside Convert Mapping | **GAP** (expected) | Pre-origins / non-canonical until Origins v1: `create_client_account_service`, Lead `convert_client_lead` HTTP, entity-profile `create_client_from_lead_conversion`. Canonical conversion: `convert_sales_inquiry_mapping` only. |
| 6 | Traceability lifecycle | **PASS** | Chain SI → flights → review? → convert → ClientAccount; omit review link when `not_required` / cancelled; write-once; orphan fail-closed. Lineage is **conversion-shaped only** — manual ClientAccount out of scope (Origins v1). |

---

## 3. Open product gaps (before end-to-end claim)

These are **architecture follow-ups**, not silent exceptions:

1. **Wire product convert** to `convert_sales_inquiry_mapping` (retire Sales spine use of Lead `convert-client` without review).  
2. **Convert must consume Review SoT** (`match_existing` / `create_new`) — gate alone is insufficient.  
3. **Demote Lead in Sales UI/API** to transport facade; SalesInquiry is product SoT.  
4. **ClientAccount Creation Origins v1** — name truthful origins; do not fake Lead/SalesInquiry/Flights for manual create.  
5. **Capability UI** — display-only after Origins docs; UI must not invent domain decisions.

Capability UI must not start until Origins v1 is merged. Closing gaps 1–3 may proceed in thin PRs interleaved with Capability UI, but claiming “Marketing → Intake → CRM Client complete” requires 1–3.

---

## 4. State machine (aligned)

Inquiry statuses used by domain convert:

| Status | Role |
|--------|------|
| `received` | Initial intake handoff |
| `open` | Active; convertible when review not blocking |
| `reviewing` / `waiting_for_information` | Work states; convertible set includes them |
| `review_required` | Ambiguous match open; convert blocked by review gate |
| `converted` | Terminal success for conversion spine; idempotent convert replay |
| `rejected` / `closed` / `abandoned` | Terminal blocked |

Review SoT (`ambiguous_match_review_v1.status`):

| Status | Convert |
|--------|---------|
| `not_required` | Allowed (no review link in lineage) |
| `required` | Blocked |
| `resolved_match` / `resolved_create_new` | Allowed after resolve |
| `cancelled` | Treated as non-blocking for lineage omit; no public cancel entrypoint yet |

```text
[Forms submit] → Flights destination
  ├─ FAIL → no SalesInquiry
  └─ OK → SalesInquiry (received/open)
           ├─ unique match → review not_required
           ├─ ambiguous → review_required (convert blocked)
           └─ resolve → open + resolved_* 

[open + review not blocking + destination confirmed]
  → Convert Mapping → ClientAccount + lineage (conversion origin)
```

Capability evaluation remains a **Sales-owned contract step**; runtime Capability UI is out of this seal.

---

## 5. Ingress scope (amended)

**INV-SI-02 (clarified):** SalesInquiry is created/attached only via the Sales intake port after Flights handoff for the **advertising / intake spine**.

**Not claimed:** SalesInquiry is the only way a ClientAccount may exist.

| Path to ClientAccount | Origin (see Origins v1) | In Pipeline v1 spine? |
|-----------------------|-------------------------|------------------------|
| Convert Mapping after SalesInquiry | `sales_inquiry_conversion` | Yes |
| Manual creation | `manual_creation` | No — separate canon |
| Legacy Lead / Stage 1A / entity-profile create | pre-origins / migrate | No — must not pretend to be Flights conversion |

---

## 6. Invariants retained

All Flow Spec INV-SI-01…10 remain in force for the intake spine, with INV-SI-02 clarified as above.

Additional seal invariants:

- **INV-SDP-01** — Convert Mapping is the only **canonical** inquiry→ClientAccount writer for conversion origin.  
- **INV-SDP-02** — Traceability for conversion is write-once on SalesInquiry; never rebuilt.  
- **INV-SDP-03** — Product paths that create ClientAccount without review gate or without truthful origin are **non-canonical** until rewired or Origins-covered.

---

## 7. History

- 2026-07-20: Phase 2 domain slices 1–4 merged; architectural revision recorded; domain contracts sealed; product wiring gaps listed; ingress wording amended.
- 2026-07-20: ClientAccount Creation Origins v1 landed — next is Capability UI (display-only), then manual create service.
