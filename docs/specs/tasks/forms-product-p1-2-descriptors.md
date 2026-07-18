# Forms Product Layer P1.2 — Component Descriptors

**Status:** **ACTIVE** (design · merge `733bd85e` / [PR #48](https://github.com/igortatarynovich/HostFlow/pull/48) opened the READY gate; this doc is implementation canon)  
**Prerequisite:** P1.1 Registry **COMPLETE** ([`forms-product-p1-1-registry.md`](forms-product-p1-1-registry.md) · `644b102a` / #47)  
**Unlocks:** P1.3 Standard library (consumes descriptors) — **LOCKED** until P1.2 DoD  
**Builder:** **LOCKED** (until P1.3)  
**Canon:** [`forms-product-p1-field-catalog.md`](forms-product-p1-field-catalog.md)

---

## Closed / active gates

| Gate | Status |
|------|--------|
| P1.2 Design | ✅ **ACTIVE** |
| Descriptor Contract | **READY FOR IMPLEMENTATION** |
| P1.3 Standard Library | **LOCKED** (after P1.2) |
| Builder | **LOCKED** (until P1.3) |

---

## Architectural split

| Sprint | Question |
|--------|----------|
| **P1.1** | *What is a component?* (identity, version, registry) |
| **P1.2** | *How do different system parts interact with it?* (four descriptor surfaces) |

After P1.2, a component is no longer only a Registry row — it **supplies four contracts**.

---

## Goal

Standardize **four descriptor surfaces** per Catalog component so clients stop hardcoding Email/Phone specifics and only ask:

> “Give me the descriptor.”

| Descriptor | Consumer | Purpose |
|------------|----------|---------|
| **Builder Descriptor** | Builder (P2) | How the component is shown and configured in the constructor |
| **Public Descriptor** | Public Form runtime | How it is shown to the end user on a published form |
| **Validation Descriptor** | Sprint 4/5 validation | Which validation rules apply |
| **Normalization Descriptor** | Sprint 5 answers | How input is reduced to canonical form |

```text
Registry.get(id, version)
  → descriptors.builder | .public | .validation | .normalization
```

These are **descriptions, not implementations**. P1.2 must **not** create UI, HTML, React components, or public pages — only the shared contract that Builder and Public Runtime will consume later.

---

## Normative rule — declarative descriptors

**Descriptors must be declarative and must not contain executable logic.**

A descriptor describes component capabilities; it does **not** run code.

Consequences:

1. The same contract can drive web UI, mobile, and future clients without tying to one technology.  
2. Field Catalog stays a **platform foundation**, not an internal Builder library.  
3. Execution (validate/normalize/render) happens in runtime engines that **interpret** descriptors — not inside the descriptor payload.  
4. No lambdas, eval, or embedded callables in stored descriptor documents.

---

## Scope

### In

- Stable descriptor contract ids / shapes for the four surfaces  
- Attach descriptors to registered `ComponentRecord` (or adjacent Catalog API)  
- Resolve descriptors via registry (exact + compatible resolution from P1.1)  
- Declarative-only payloads (JSON/schema-like data)  
- Contract tests: every registered component can expose all four descriptors (may be minimal stubs)  
- Compose existing Sprint 4/5 validation & normalization hooks — do not fork them  

### Out

- **UI renderers** (actual React/widgets) — descriptors only; UI in P2/P4  
- **Standard library** components (P1.3) — **LOCKED**  
- Extension API (P1.4)  
- Builder unlock  
- Executable logic inside descriptors  
- Migrations (unless strictly required; prefer code registry)  

---

## DoD (implementation gate)

- [ ] Four descriptor surfaces defined and documented  
- [ ] Registry/API returns descriptors for a component version  
- [ ] Clients can fetch without knowing Email/Phone internals  
- [ ] Descriptors are declarative (no executable logic) — gate-tested  
- [ ] Validation/Normalization descriptors compose Sprint 4/5 contracts  
- [ ] Contract + gate tests green  
- [ ] No Builder UI · no stdlib pack · P1.3 and Builder remain LOCKED  

---

## History

- 2026-07-18: Opened as READY after P1.1 merge `644b102a` (#47).  
- 2026-07-18: Design **ACTIVE** after #48 (`733bd85e`); Descriptor Contract READY FOR IMPLEMENTATION; declarative-only rule added.
