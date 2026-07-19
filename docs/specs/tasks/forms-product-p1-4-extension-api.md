# Forms Product Layer P1.4 — Extension API

**Status:** **READY** (after P1.3 merge)  
**Prerequisite:** P1.3 Standard Library **COMPLETE**  
**Preferred before:** Product Layer P2 (Builder)  
**Canon:** [`forms-product-p1-field-catalog.md`](forms-product-p1-field-catalog.md)

---

## Goal

Allow modules (Recruitment, HR, Fleet, Service, …) to register **their own** Catalog components through a public extension API — same Registry + Descriptors contracts as the Standard Library.

No Catalog-core special cases. No Builder changes required to discover new components.

---

## Scope (preview)

### In

- Module registration entrypoint (platform-wide, not tenant-private types)  
- Ownership / namespace conventions (`recruitment.field.*`, …)  
- Isolation tests: module components resolve via public APIs  

### Out

- Builder UI (P2)  
- Themes / Analytics  
- Rewriting Registry / Descriptors  

---

## History

- 2026-07-18: Opened as READY when P1.3 lands.
