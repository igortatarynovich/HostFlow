# Naming & Identifiers — platform inventory

**Hierarchy:** L2 — indexes naming rules and conflict evidence; **not** a data SoT  
**Decision record:** [`ADR-040`](../architecture/ADR-040-naming-identifiers.md)  
**Parent model:** [`ADR-038`](../architecture/ADR-038-platform-standardization-model.md) · [`platform-standardization-model.md`](platform-standardization-model.md) (area `naming_identifiers`)  
**Related:** [`object-kind-catalog.md`](object-kind-catalog.md) · [`document-type-registry-v1.json`](document-type-registry-v1.json) · [`document-type-legacy-aliases-v1.json`](document-type-legacy-aliases-v1.json)  
**Owner:** Architecture canon + platform core team  
**Slice:** Object Kind Documents / Requirements / Automation / Templates identifiers (+ compliant Field / profile / permission examples)

---

## 1. Row contract

| Field | Meaning |
|-------|---------|
| `code_family` | Named vocabulary family |
| `identifier_kind` | `uuid` \| `stable_code` \| `qualified_code` \| `legacy_alias` |
| `owner` | SoT owner for canonical codes |
| `pattern` | Naming pattern in force |
| `example_codes` | Representative codes (descriptive) |
| `conflict` | `none` or short conflict description |
| `sot_refs` | Code / doc paths |
| `notes` | Aliases, forbidden mixes, backlog |

---

## 2. Rules summary (from ADR-040)

1. Pick an **identifier kind** before inventing a string.
2. **One SoT owner** per `code_family`; others consume or alias toward it.
3. DocumentType **evaluation** codes are flat `stable_code` (ADR-018 registry).
4. Fields / profiles / permissions use `qualified_code`.
5. `legacy_alias` is one-way into the owning family; **forbidden** in evaluation / matching.
6. **Forbidden:** two bridges that normalize the same input to different “canonical” targets.
7. This inventory does **not** realign seeds; DocumentType remains `integrity=split` until a dedicated alignment PR.

---

## 3. Code family inventory

| code_family | identifier_kind | owner | pattern | example_codes | conflict | sot_refs | notes |
|-------------|-----------------|-------|---------|---------------|----------|----------|-------|
| `document_type.evaluation` | stable_code | Platform Requirements / Document Type registry (ADR-018) | flat snake_case | `national_identity_card`, `driver_qualification_card`, `psychological_certificate`, `passport`, `residence_card` | split vs ref/UI (see §4) | [`document-type-registry-v1.json`](document-type-registry-v1.json), `backend/app/document_types/registry.py` | Evaluation + requirement matching SoT |
| `document_type.ref` | stable_code | Platform Reference | flat snake_case | `id_card`, `code_95`, `psychotest`, `passport` | split vs evaluation | `document_reference_sync.py`, `ref_document_types`, alembic seed `202608130002_…` | Operational ref catalog — **not** evaluation SoT |
| `document_type.ui_module` | stable_code + aliases | Documents / Recruitment UI definitions | module codes + `canonical_ref_code` | `national_id` → ref `id_card` | bridges to **ref**, not evaluation | `backend/app/document_types/definitions.py` | Must not be treated as evaluation SoT |
| `document_type.ocr_keywords` | (non-SoT list) | Scanner / OCR | keyword labels | `id_card`, `identity_document`, `qualification_card` | not aligned to evaluation codes | `backend/app/scanner/document_types.py` | **Keyword classifier only** — not evaluation SoT |
| `document_type.legacy_alias.eval` | legacy_alias | ADR-018 alias map | one-way → evaluation | `id_card` → `national_identity_card` | conflicts with ref bridge target | [`document-type-legacy-aliases-v1.json`](document-type-legacy-aliases-v1.json) | Allowed: input normalize / migration; forbidden in requirement evaluation |
| `document_type.legacy_alias.ref` | legacy_alias | Ref canonical bridge | one-way → **ref** codes | `id` → `id_card` | **dual bridge** vs eval aliases | `backend/app/services/document_type_canonical_bridge.py` | Forbidden pattern until alignment: opposite target family |
| `field_registry` | qualified_code | Platform Field Registry | `module.entity…` | `recruitment.candidate.first_name`, `platform.identity.citizenship` | none (compliant example) | Field Registry manifests / [`field-registry-card-configuration.md`](field-registry-card-configuration.md) | — |
| `entity_profile` | qualified_code | Entity Profile registry | `module.entity.variant` | `service_sales.targeted_advertising` | none (compliant example) | [`entity-profile-definition-registry.md`](entity-profile-definition-registry.md) | Presentation profiles may add a final segment |
| `permission` | qualified_code | Users / Roles / Permissions | dotted capability/permission ids | `users.roles_access`, `platform.tenants`, `billing.subscription` | none (compliant example) | ADR-036 / `auth/trust_roles.py` | Presets ≠ roles |
| `runtime_instance` | uuid | owning module / hub | UUID | document id, tenant id | none | ORM models | Never use registry codes as PKs |

---

## 4. DocumentType conflict evidence (descriptive)

| Meaning (informal) | Evaluation SoT (`stable_code`) | Ref / UI common code | OCR / other labels | Notes |
|--------------------|--------------------------------|----------------------|--------------------|-------|
| National ID card | `national_identity_card` | `id_card` | `id_card`, `identity_document`, `national_id` | Primary split called out in object-kind-catalog |
| Driver Code 95 / qualification | `driver_qualification_card` | `code_95` | `qualification_card` | Eval aliases also map `code_95` → evaluation code |
| Psychological certificate | `psychological_certificate` | `psychotest` | (varies) | Ref short name ≠ evaluation name |
| Residence document | `residence_card` | (often same) | `residence_permit`, `karta_pobytu` | Aliases → evaluation in ADR-018 map |

**Dual-bridge disagreement (forbidden pattern):**

- Eval aliases: `id_card` → `national_identity_card` ([`document-type-legacy-aliases-v1.json`](document-type-legacy-aliases-v1.json)).
- Ref bridge: legacy / module strings → `id_card` (`document_type_canonical_bridge.py` + `SYSTEM_CODES`).

Until alignment, **evaluation consumers** must not treat ref-normalized `id_card` as ADR-018 evaluation truth without an additional map into the evaluation registry.

---

## 5. Alignment backlog (not executed in ADR-040)

1. Choose convergence direction consistent with ADR-040: **evaluation `stable_code` wins** for Requirement Evaluation / gates.
2. Retire or re-target the ref bridge so it does not publish a competing evaluation canonical.
3. Update ref seeds / packs / UI `canonical_ref_code` / frontend labels as needed.
4. Keep OCR as keyword → evaluation normalize, not as a third SoT.
5. Flip Object Kind Catalog DocumentType `integrity` from `split` → `aligned` only after the above.

---

## 6. History

- 2026-08-13: Initial L2 naming inventory under ADR-040; DocumentType split documented; area `naming_identifiers` → exists (runtime alignment deferred).
