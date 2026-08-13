# ADR-040: Naming & Identifiers

**Status:** Accepted  
**Date:** 2026-08-13  
**Layer of change:** Vocabulary (Naming & Identifiers) | Meta-canon + conflict inventory  
**Trusted base:** `integration/release-product-a-b`  
**Related:** [`ADR-037`](ADR-037-platform-object-kind-catalog.md) · [`ADR-038`](ADR-038-platform-standardization-model.md) · [`ADR-039`](ADR-039-state-lifecycle-inventory.md) · [`ADR-018`](ADR-018-requirement-policy-evaluation-model.md) · [`ADR-009`](ADR-009-document-hub-platform-layer.md) · [`ADR-036`](ADR-036-four-trust-roles-rbac.md) · L2 [`../platform/naming-identifiers.md`](../platform/naming-identifiers.md) · [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md)

**L0 checklist:** No new L0 P-rule; does not rewrite Passport/Manifest; fills ADR-038 area `naming_identifiers` with **naming rules + conflict inventory**, not a runtime code realignment; does not flip DocumentType `integrity=split` → `aligned`.

---

## Context

ADR-038 marked **Naming & Identifiers** as `gap` and noted that DocumentType `integrity=split` cannot be remediated without a platform rule for **which code is canonical, who owns it, and how aliases may point**.

Today evaluation uses ADR-018 codes such as `national_identity_card`, while Platform Reference seeds / UI bridges use `id_card`, and OCR keeps a separate keyword list. Two alias maps disagree on the target. Without a naming canon, every module invents a local “canonical” string.

---

## Decision

### 1. Identifier kinds (closed)

| Kind | Shape | Used for |
|------|-------|----------|
| `uuid` | UUID v4 (string) | Persisted entity instances (`document.id`, tenant ids, …) |
| `stable_code` | flat `snake_case` | Platform registry codes with a single SoT owner (DocumentType evaluation codes, pack codes, …) |
| `qualified_code` | dotted `segment.segment…` | Cross-module vocabulary that needs a namespace (Field Registry, Entity Profile, permissions / capabilities) |
| `legacy_alias` | any historical string | **Input normalization / migration only** — never evaluation or matching SoT |

Do not invent a fifth kind for “short marketing codes” or “OCR labels.” Those are either `legacy_alias` or non-SoT keyword lists.

### 2. Namespace rules

| Family | Kind | Rule |
|--------|------|------|
| DocumentType (evaluation) | `stable_code` | Flat platform codes; **no** `documents.` prefix |
| Document packs / requirement definition codes | `stable_code` | Flat; owner owns the registry |
| Field Registry fields | `qualified_code` | e.g. `recruitment.candidate.first_name` |
| Entity profiles / presentation profiles | `qualified_code` | e.g. `service_sales.targeted_advertising` |
| Permissions / capability ids | `qualified_code` | e.g. `users.roles_access`, `platform.tenants` |
| Runtime instances | `uuid` | Never reuse registry codes as primary keys |

**Forbidden:** a second parallel `stable_code` vocabulary for the same evaluation meaning (e.g. treating `id_card` as evaluation-equal to `national_identity_card` without going through a single alias map to the evaluation SoT).

### 3. One SoT owner per code family

Every `code_family` has exactly one owner that defines the canonical set of codes. Other layers may **consume** or **alias toward** that set; they must not publish a competing canonical list for the same purpose.

| Code family | Canonical owner | Notes |
|-------------|-----------------|-------|
| `document_type.evaluation` | Platform Requirements / Document Type registry (ADR-018) | SoT for Requirement Evaluation and stage gates |
| `document_type.ref` | Platform Reference (`ref_document_types`) | Operational reference catalog — **not** a second evaluation SoT |
| `document_type.ocr_keywords` | Scanner / OCR module | Keyword classification only — **not** evaluation SoT |
| `field_registry` | Platform Field Registry | `qualified_code` |
| `entity_profile` | Entity Profile registry | `profile_code` as `qualified_code` |
| `permission` | Users / Roles / Permissions (ADR-036) | `qualified_code` |

### 4. Alias policy

1. **One-way:** `legacy_alias` → canonical code of the **owning** family.
2. **Forbidden in evaluation / policy matching / stage gates** (ADR-018 alias JSON already states this).
3. **No dual bridges with opposite targets.** Example of the forbidden pattern: evaluation aliases map `id_card` → `national_identity_card` while a ref bridge maps legacy strings → `id_card` as if `id_card` were evaluation-canonical.
4. Until the DocumentType alignment PR lands, consumers that need evaluation semantics must normalize through the **evaluation** alias map (or store evaluation codes), not through the ref bridge alone.

### 5. Integrity vs this ADR

Object Kind Catalog may keep `integrity=split` while naming conflicts remain in runtime/seeds. **This ADR does not flip DocumentType to `aligned`.** Alignment is a dedicated follow-on PR that applies these rules to seeds, bridges, and UI.

### 6. Enforcement (future)

Naming lint / registry CI is **planned** (`platform-standardization-model` area notes) and is not shipped in this PR. Until then, architecture review + docs-lint inbound refs bind the canon.

---

## Out of scope (explicit)

- Changing `document-type-registry-v1.json`, ref seeds, Alembic, `definitions.py`, OCR keyword lists
- Flipping DocumentType `integrity` to `aligned`
- Shared status enums / Design Semantic Visual Language
- Data Types, Relationships, Actions / Events canons
- Renaming Candidate / Lead / Vacancy domain codes

---

## Explicit next

1. **DocumentType code alignment PR** — converge ref/UI/OCR consumers toward evaluation `stable_code` (or a single approved bridge), then set Object Kind `integrity=aligned`.
2. Data Types: **done** ([`ADR-041`](ADR-041-data-types.md)). ADR-038 sequence continues with **Relationships**.

---

## Architecture Review Checklist (L0)

- [x] P-01…P-05 respected — no new capability Passport
- [x] Does not invent a second DocumentType evaluation SoT
- [x] Aligns with ADR-018 evaluation registry ownership
- [x] Platform-first — rules before module-local “canonical” strings
- [x] L0 freeze untouched

---

## Consequences

- Positive: Naming area becomes `exists`; DocumentType split has an explicit remediation contract; Field / profile / permission dotted codes are recognized as compliant examples.
- Negative: runtime remains split until the alignment PR; dual bridges stay documented as debt.
- Follow-on: DocumentType alignment; ~~Data Types~~ (ADR-041); Relationships (ADR-038 sequence).

---

## Alternatives considered

1. **Align seeds in the same PR** — rejected; one concern — naming canon first (matches ADR-037…039 docs-only pattern).
2. **Dotted DocumentType codes** (`documents.national_identity_card`) — rejected; evaluation registry is flat; would force a mass rename without benefit.
3. **Treat ref `id_card` as evaluation SoT** — rejected; contradicts ADR-018 and requirement definitions.

---

## Cross-references (updated in same change set)

- [`../platform/naming-identifiers.md`](../platform/naming-identifiers.md) — L2 rules + conflict inventory
- [`../platform/platform-standardization-model.md`](../platform/platform-standardization-model.md) — area `naming_identifiers` → `exists`
- [`ADR-038-platform-standardization-model.md`](ADR-038-platform-standardization-model.md) — next-pointer update
- [`../platform/object-kind-catalog.md`](../platform/object-kind-catalog.md) · [`architecture-guide.md`](architecture-guide.md) · [`module-catalog-and-routing-map.md`](module-catalog-and-routing-map.md)
