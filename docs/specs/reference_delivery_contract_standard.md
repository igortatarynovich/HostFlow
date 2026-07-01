# Reference Delivery Contract Standard (REF-2)

Status: accepted baseline  
Scope: system reference layer delivery contract for Recruitment, HR, Documents, Fleet and future modules.

## 1. Purpose

Define one canonical way to:
1. store reference data;
2. store rule logic;
3. deliver reference data + rules to modules;
4. prevent modules from bypassing the reference facade.

M5 eligibility runtime is frozen as `consumer-preview` until REF-2/REF-3/REF-4/REF-5 gates are closed.

## 2. Canonical Architecture

Flow:
`module -> Reference Service Facade -> reference catalogs + rule engine -> canonical response`

Modules are consumers only. They must not know table layout or rule storage internals.

## 3. ReferenceContext (request contract)

All module requests must provide context in canonical shape:

```json
{
  "tenant_id": "uuid",
  "module": "recruitment|hr|documents|fleet|clients|other",
  "entity_type": "candidate|employee|client|vacancy|vehicle|assignment|company",
  "entity_id": "uuid|null",
  "work_country": "ISO-3166-alpha2|null",
  "citizenship": "ISO-3166-alpha2|null",
  "residence_status": "code|null",
  "position_category": "code|null",
  "stage": "recruitment|handoff|hr|onboarding|operations|payroll|null",
  "employment_type": "code|null",
  "client_id": "uuid|null",
  "vacancy_id": "uuid|null",
  "locale": "en|pl|uk|ru|...",
  "as_of": "ISO datetime|null"
}
```

## 4. ReferenceResponse (response contract)

The facade response must include data + explainability:

```json
{
  "version": "contract-version",
  "reference_version": "catalog/ruleset version",
  "context_echo": {},
  "items": [
    {
      "item_type": "country|citizenship|document_type|document_field|rule|pack_item",
      "code": "canonical_code",
      "label": "localized label",
      "visible": true,
      "required": false,
      "reason": "why item is present/required",
      "source": {
        "type": "system|pack|tenant_override|fallback",
        "code": "source-code"
      },
      "rules": [],
      "validation": {}
    }
  ],
  "applicability": {
    "expected_documents": [],
    "missing_documents": [],
    "unverified_documents": [],
    "expired_documents": []
  },
  "errors": []
}
```

## 5. Rule Model (canonical)

Each rule is normalized and versioned:

```json
{
  "rule_code": "string",
  "scope": "system|country|industry|pack|tenant",
  "priority": 100,
  "condition": {
    "work_country": ["PL"],
    "citizenship_group": ["non_eu"],
    "position_category": ["driver"],
    "stage": ["hr"]
  },
  "effect": {
    "required": true,
    "criticality": "informational|operational|required|compliance_critical|work_blocking",
    "due_point": "before_client_submission|before_arrival|before_employment|before_first_route"
  },
  "override_policy": "system_locked|tenant_can_strengthen|tenant_can_relax_non_critical",
  "valid_from": "ISO datetime",
  "valid_to": "ISO datetime|null",
  "source": "catalog/pack/tenant"
}
```

## 6. Versioning Policy

1. `contract_version` versions the API shape.
2. `reference_version` versions catalogs + rules snapshot.
3. Breaking contract changes require a new contract version.
4. Rule/data changes within same contract are allowed with bumped `reference_version`.

## 7. Override Policy

Tenant override is allowed only by policy:
1. enable/disable applicable non-critical items;
2. strengthen requirement (`optional -> required`) for tenant scope;
3. adjust reminders/owners/instructions.

Tenant override is forbidden for:
1. canonical identity (code/category/purpose);
2. compliance domain remapping;
3. replacing system legal document meanings;
4. weakening system work-blocking requirements.

## 8. Module Usage Rules

Mandatory usage:
1. Recruitment/HR/Documents/Fleet call facade only.
2. Modules pass context and render response; no custom rule engines.
3. Module APIs may expose legacy compatibility fields, but values must be derived from facade response.

## 9. Forbidden Patterns

Forbidden in module runtime code:
1. direct SQL/table reads for reference decision logic;
2. local `if/else` decision matrices for document requirements;
3. hardcoded domain/severity/action strings for compliance decisions;
4. creating blockers outside canonical resolver/facade;
5. direct use of legacy `doc_type` as source of truth.

## 10. Gate Policy (`foundation ready?`)

No higher-layer work (M5+) unless these are green:
1. REF-2 gate: contract approved and published.
2. REF-3 gate: facade implemented as single read path.
3. REF-4 gate: catalogs/rules complete for countries/citizenship/doc types/fields/packs.
4. REF-5 gate: Recruitment + HR switched to facade-only context->response.

## 11. Implementation Boundaries

Allowed legacy locations during transition:
1. sync/backfill services;
2. resolver fallback paths;
3. compatibility tests.

Not allowed:
1. new module-side reference logic;
2. new module-local blocker engines.

## 12. Immediate Next Steps

1. Implement REF-3 `ReferenceServiceFacade` with this contract.
2. Add contract conformance tests for context/response shape.
3. Add static scan gate to reject forbidden patterns in module runtime code.
