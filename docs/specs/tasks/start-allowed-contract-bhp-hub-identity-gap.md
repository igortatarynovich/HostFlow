# Gap-fix: Contract/BHP evidence identity ↔ Hub storage

**Status:** **PASS** (2026-09-15)  
**Layer:** L3 proof / gap-fix — **not** Full Spine reopen · **not** catalog spam for Walk 4  
**Phase class:** product  
**Opened:** 2026-09-15  
**Closed:** 2026-09-15  
**Parent STOP:** [`three-host-full-spine-gate-pem1.md`](three-host-full-spine-gate-pem1.md) Walk journal 3 — candidate `86d19b53-123c-40d9-96e3-ff43641232f1`  
**Depends on:** DOCUMENT_REQUIRED Hub alias PASS · ESA start_allowed runtime · Documents meta schemas  
**Does not open:** Full Spine PASS · inventing unrelated Hub types · `if contract` / `if bhp` in start_allowed · meta.type as storage SoT · **spine topology** (see [`ADR-042`](../architecture/ADR-042-spine-policy-separation.md))

> Walk 3 proved Ready → Transfer → Formalize → Employee.  
> Halt was **admit-to-work evidence resolution**: Contract/BHP Hub identity.  
> **Re-scope (2026-09-15):** this PASS is a **policy evidence / Hub storage identity** fix. It does **not** prove Full Spine kernel. Further document gap-fixes must not be framed as spine topology.

---

## Original Goal → Completion Proof

**Problem this gap must permanently remove:**  
`start_allowed` cannot see Contract/BHP Hub rows because inbound create collapses those identities to `additional_document`, while Medical (`medical_certificate`) persists and resolves.

**Completion proof (named consumer):**

```text
create Hub employment_contract + bhp (canonical storage codes)
  → start_allowed._pick_doc resolves via shared storage-key authority (no type-specific if)
  → Contract + Medical + BHP evidence views project
  → start_allowed=true when structured facts hold
  → machine gate green
  → Walk 4 new person (not 86d19b53-…)
```

**Decision:** **PASS** — machine gate `start-allowed-contract-bhp-hub-identity-gate` green.

---

## Inventory (locked 2026-09-15)

| Question | Finding |
|----------|---------|
| Canonical Contract code? | **Yes** — Platform Reference `employment_contract`; legacy `contract` / `umowa_o_prace`. |
| Canonical BHP code? | Documents/HR-named `bhp` (adaptation + meta + expected-docs); was registry-weak — closed by adding Platform Reference `bhp` + legacy aliases. |
| What should Hub store? | Physical codes `employment_contract` and `bhp` (not `additional_document`). |
| Is `meta.type` typing authority? | **No.** |
| Why Medical works? | Hub definition present → normalize keeps code. Contract/BHP Hub definitions were missing → `additional_document`. |
| Existing bridge? | `hub_storage_keys_for_requirement_code` existed; `_pick_doc` bypassed it — now uses `document_storage_type_matches`. |

### Implementation (closed)

| Surface | Change |
|---------|--------|
| Hub `definitions.py` | Restore `employment_contract` + `bhp` (+ aliases) |
| Platform registry + legacy aliases | `bhp` ref code; `umowa_o_prace`→contract; BHP aliases |
| `document_storage_type_matches` | Shared pick authority |
| `start_allowed._pick_doc` | Uses shared match — no type-specific `if` |

---

## Machine proof — PASS

**Gate id:** `start-allowed-contract-bhp-hub-identity-gate`  
(`backend/tests/platform/test_start_allowed_contract_bhp_hub_identity_gate.py`; CI wired)

---

## Next after PASS

Restart backend → **Walk 4** new person from scratch. Do **not** resume `86d19b53-…`. Full Spine remains **NOT PASS** until composition PASS.
