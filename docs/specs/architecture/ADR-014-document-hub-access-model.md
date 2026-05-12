# ADR-014: Document Hub — access model

**Status:** Accepted (architecture). **Supersedes ad-hoc document access reasoning in implementation discussions. Existing implementation is migrated incrementally.**

**Related:** [ADR-009 — Document Hub platform layer](ADR-009-document-hub-platform-layer.md), [Hard invariants — Recruitment, HR, Document Hub](invariants-recruitment-hr-document-hub.md), [Handoff contract](handoff-contract.md), [ADR-003 — tenant / company boundaries](ADR-003-tenant-company-module-data-boundaries.md), [Phase 1 epic & tasks (tracker import)](ADR-014-phase1-implementation-epic.md).

---

## 1. Context

- Today, candidate-facing document flows are often experienced as **“a tab on the candidate”**. That coupling is fragile: the same document must survive **handoff**, **HR**, **transport compliance**, **finance**, **multi-office** operations, and **client portal** views without duplicating ACL logic per surface.
- **`own_company_id` / `X-Own-Company-Id` (workspace slice)** is required for **placement, filtering, and UX workspace**. It must **not** become an independent **authorization source of truth** for whether a user may access the **owner entity** (e.g. candidate). When it does, the system diverges: the candidate card is visible under tenant/list rules, while document APIs return **404/403** for the same user — a contract bug, not a security feature.
- **Document ≠ file**: a file is a **version or attachment**; a **document** is a **business object** with lifecycle, policy, compliance meaning, process state, and audit. Conflating them blocks re-verification, renewals, multi-version history, generated/signed artifacts, external sync (e.g. KSeF), and module-specific visibility without copying blobs.

---

## 2. Decision

### 2.1 Canonical principles (normative wording)

1. **Workspace vs authorization**

   > **Workspace limits where the document is placed and filtered. It must not independently decide whether the user is authorized to access the owner entity.**

2. **Document vs file**

   > **A document is a business object with lifecycle, policy and audit. A file is only one version or attachment of that document.**

### 2.2 Separation of concerns

Access and semantics are split explicitly:

| Concern | Meaning |
|--------|---------|
| **Owner access** | User may access the **owner entity** (candidate, employee, client, …) under tenant + product rules (existing candidate ACL / scope paths today; unified later). |
| **Document context** | For a given operation, which **document** rows and which **fields** are visible (module, process stage, handoff state). |
| **Workspace slice** | `own_company_id` / header: **where** documents are filed and **how lists are filtered**, not a substitute for owner access. |
| **Visibility scope** | Which modules / channels may see the document or a **redacted view** (recruitment vs HR vs transport vs finance vs client portal). |
| **Process locks** | Handoff, employment, settlement, or compliance steps **freeze or narrow** mutations / visibility regardless of role defaults. |

### 2.3 Single infrastructure gate

- All document APIs **must** obtain a resolved **document access context** through a single component: **`DocumentAccessResolver`** (name normative; implementation may start as a thin wrapper over existing candidate access + document policy hooks).
- **No new** `ensure_*_scope` chains inside the documents module that re-derive owner authorization from workspace headers alone.
- The resolver is **policy-driven, not module-driven** (see **§7**): new surfaces attach **policies / rules**, not parallel “HR vs finance” resolver implementations.

---

## 3. Non-goals (this milestone)

- **No** full **Document Hub UI** rebuild in one release.
- **No** rewrite of **all** document HTTP routes in a single PR; existing candidate document routes remain a **facade** over the same domain until migrated.
- **No** mandatory implementation of **OCR**, **KSeF**, **e-signature providers**, or full **external portal** product scope inside this ADR’s first implementation slice.

---

## 4. Deprecated patterns

The following are **deprecated** for new code and should be removed when touching call sites:

| Deprecated | Replace with |
|------------|----------------|
| Local `ensure_*_scope` helpers **inside documents HTTP handlers** that infer **owner** authorization from `X-Own-Company-Id` alone | **`DocumentAccessResolver`** + shared owner-access path |
| **404/403** justified only by **mismatch** between workspace header and `Candidate.own_company_id` while the user already has **valid owner access** | Resolver: **workspace resolves placement/filter**; **owner access** comes from the same rules as the entity card |
| Treating **file upload** as the **document lifecycle** (status, verification, expiry, audit) | **Document** aggregate for lifecycle; **file** entities for bytes / versions |
| **Different ACL rule stacks** copy-pasted across recruitment / HR / finance / transport for the same document | **One resolver** + module-specific **context links** / policies (per ADR-009 links) |

---

## 5. Migration path

1. **Align contracts** — owner visibility and document list/summary must not contradict each other for the same authenticated context (workspace may only narrow document rows, not “hide” the owner after the fact).
2. **Remove ad-hoc checks** — delete or bypass local `ensure_*` in documents routes in favor of resolver inputs (incremental PRs).
3. **Introduce `DocumentAccessResolver`** — initially may delegate to existing `get_candidate_with_labels` / ACL + document policy; grow to handoff, HR, transport, finance contexts.
4. **Migrate API** — `summary` / `list` / `checklist` / `export` / `create` / `update` / `delete` on candidate document façade call the resolver for **document context**; owner access stays centralized.
5. **Add document context links** (per ADR-009 `Document Link` direction) — reuse one `Document` across modules without file copy.
6. **Hub UI** — thin clients on top of stable APIs and resolver.

Rollout detail: **§6 Implementation phases** (below).

---

## 6. Implementation phases

### Phase 1 — Resolver foundation

**Goal:** remove duplicated authorization logic from the documents API.

**What this phase is (normative framing):** **not** “build Document Hub”. It delivers an **infrastructure boundary**, **access normalization**, and a **migration foundation** for HR / transport / finance. Skipping straight to Phase 5 (Hub UI) or a full policy graph is **out of scope** and will collapse the rollout.

#### Phase 1 — implementation scope (this milestone)

Implement **only** the foundation resolver layer described here. **Policy graph**, **capabilities engine**, and **generic DSL** are **not** part of Phase 1.

**Allowed**

- `DocumentAccessResolver`
- `DocumentAccessContext`
- **Owner access** resolution (reuse / wrap existing candidate access logic — single path)
- **Resolved workspace slice** (placement / filter input, not owner authorization)
- **Visibility** stub (explicit extension point, safe default)
- **Process lock** stub (explicit extension point, safe default)
- **Policy-driven structure** (one resolver + pluggable policy hooks / rules — no per-module resolver forks)
- **Migration of one document flow** end-to-end first (e.g. summary → then expand), **provided** acceptance criteria below are met for the **candidate documents-db surface** in scope of the epic

**Forbidden**

- Hub UI
- Policy graph (evaluation graph as a productized engine)
- Capabilities engine (full capability-based IAM product)
- Generic DSL for policies
- Multi-owner graph
- Document versioning redesign
- OCR / signature / KSeF
- Module-specific ACL systems (`ensure_hr_document_scope`, transport/finance forks, etc.)

#### Phase 1 — acceptance criteria (minimum)

1. `GET …/documents/summary` (and the code path behind it) **does not** use local `ensure_*_scope` / header-only owner authorization.
2. **`X-Own-Company-Id` alone** must **not** produce **“Candidate not found”** (or equivalent owner 404) when owner access is valid per the entity card / list scope (see **§11 scenario A**).
3. **All** candidate **documents-db** HTTP endpoints in scope **invoke** the resolver (or a single delegated helper) **before** reading or mutating document rows — stubs allowed for visibility / locks until policies exist.
4. **Candidate / owner access** is determined **only** via the **owner access** leg of the resolver (shared with card access rules), not ad-hoc copies in the documents router.
5. **Workspace** is used **only** as **slice resolution** (filter / placement), not as the sole authorization gate for the owner entity.
6. **Acceptance scenario A** (**§11**) is covered by an **automated test** (or equivalent CI check) that fails on regression.
7. **No new** `ensure_*_document_scope` (or equivalent module-specific document ACL helpers) may be introduced; extend **policies** on the existing resolver instead.

#### Phase 1 — primary architectural outcome

Not “a new ACL product”. Rather:

- **Remove duplicated access logic** around documents.
- **Centralize the document authorization contract** at the resolver boundary.
- **Lay the foundation** for HR / transport / finance without shipping their UI or full policy engines in this phase.

**Out of scope (reminder, shorter list):**

- Hub UI
- document links graph
- multi-owner
- versioning
- signature / OCR

**Tracker import:** ready-made **Epic + Tasks 1–5** + **PR-1…PR-4 merge sequence** + execution risks for Linear/Jira — [ADR-014-phase1-implementation-epic.md](ADR-014-phase1-implementation-epic.md).

---

### Phase 2 — API migration

Phase 1 **wires** endpoints through the resolver (stubs allowed). Phase 2 **replaces** remaining ad-hoc authorization and **fills in** visibility / process-lock behavior using policies — without introducing a separate policy graph product (see **§12**).

#### Phase 2 — Viewer channel read visibility (policy functions, not a graph)

Clients declare the **viewing surface** with HTTP header **`X-Document-Viewer-Channel`**: `recruitment` \| `hr` \| `transport` \| `finance`. If the header is **omitted**, the channel defaults to **`recruitment`**. **Invalid** values → **HTTP 422** (no silent fallback to a “nearest” channel).

**Read policy (implemented as plain functions on the resolver context, not a DSL):**

- Each channel may read document types whose **primary visibility scope** is in **`{ that_channel, shared }`**.
- **`shared`** is reserved as a **cross-module bridge** (e.g. raw `doc_type` values whose normalized / raw code is treated as under the shared scope — see implementation). **Driver license** types are intentionally classified under **`shared`** primary scope until a finer graph exists, so **recruitment** and **transport** both retain access without duplicating rows.
- **Single-document reads** (metadata, file URLs, checks): if the row exists but is **invisible** to the viewer channel, the API returns **404** (avoid cross-surface existence leaks).

**Mutations (conservative until an explicit product expansion):** document **create / patch / presign / review check / mock-upload** require viewer channel **`recruitment`**. **Destructive** operations use the same viewer rule **and** existing **process-lock** tokens (**§10**).

**Observability:** at **DEBUG** log level, list/summary/export paths emit a single structured line (`document_access_visibility`) with `viewer_channel`, readable scopes, DB row totals vs viewer-visible counts, and synthetic counts where applicable. When the environment variable **`HOSTFLOW_DOCUMENT_ACCESS_DEBUG`** is set to `1` / `true` / `yes`, **JSON** responses for **`GET …/documents/summary`** and **`GET …/documents/export.json`** may include an extra object key **`document_access_trace`** with the same diagnostics (for local dev / CI only — do not enable in production without review).

This layer is **not** handoff-aware policy, **not** a role matrix, and **not** finance-specific rules until real finance document types exist in the catalog.

Move **summary**, **list**, **checklist**, **export**, **create** / **update** / **delete** onto the resolver instead of:

- `ensure_candidate_own_company_scope` (and similar ad-hoc gates)
- header-only checks as authorization
- local ACL copies inside the documents router

---

### Phase 3 — Document entity normalization

Split:

- **Document** — business object
- **DocumentFile** — blob / version

Introduce (at data model + API level):

- lifecycle state
- verification state
- audit
- expiry
- file versions

---

### Phase 4 — Context links

`Document` ↔:

- Candidate  
- Employee  
- Client  
- Vehicle  
- Finance entity  
- Service / Order  

(Aligned with ADR-009 **Document Link**; graph queries and cross-module reuse without copying files.)

---

### Phase 5 — Hub UI

Dedicated **Documents Hub** experience:

- filters
- SLA
- expirations
- verification queue
- HR review
- transport compliance
- finance docs
- client portal visibility

---

## 7. Resolver design: policy-driven, not module-driven

**Wrong (do not build):**

- “HR resolver”, “Candidate resolver”, “Finance resolver” as separate engines.

**Right:**

- **One** `DocumentAccessResolver`
- **Policies / plugins / rules** that contribute facts and constraints; modules **consume** the resolved context, they do **not** own access logic.

**Normative:**

- **Modules consume access; the resolver owns access logic.**

Otherwise, within ~12 months the codebase tends toward **multiple ACL engines** that disagree on the same document.

---

## 8. Consequences

- **Positive:** Handoff, internal transfer, multi-office, and module expansion stop fighting workspace headers; finance/transport/HR can attach policies without re-implementing candidate ACL.
- **Negative:** Short-term engineering: resolver introduction and route migration; tests must assert **resolver matrix** (owner allowed + workspace slice + document policy), not only happy-path uploads.

---

## 9. AI / implementation notes

- When adding a new module surface that shows documents, **do not** add another `ensure_<module>_scope` in the documents router; extend **`DocumentAccessResolver`** inputs or policy tables.
- When a 404 occurs on document APIs, classify: **owner access denied** vs **document not in context** vs **workspace filter empty** — distinct HTTP semantics where product allows.
- **Do not** fork the resolver per module; add **policy** (rule type, inputs, ordering, deny-by-default where required) and tests for policy interaction.

---

## 10. Implementation invariants

Use this list when reviewing **any** PR that touches document access, APIs, or storage. Violations are **architectural defects**, not style nits.

1. **Document API must not authorize owner access by workspace header alone.**
2. **Every document operation must resolve `DocumentAccessContext`** (via `DocumentAccessResolver` or its direct successor) **before** reading or mutating persisted document data.
3. **Modules may request access context, but must not implement their own document ACL** (no parallel `ensure_*` stacks for the same concern).
4. **Workspace mismatch may affect filtering / placement, but must not produce “Candidate not found” (or equivalent owner 404) by itself** when owner access is already valid for the entity card / list scope.
5. **Document lifecycle state must not be inferred from file upload state** alone (upload completes ≠ verified ≠ approved).
6. **File visibility must not be broader than document visibility** (bytes follow the document’s resolved context).
7. **Process locks must be checked before destructive mutations** (delete, replace primary file, downgrade verification, etc.).
8. **Cross-module access must be expressed through policy / context**, not duplicated endpoint-specific logic.
9. **New document owner types require resolver policy tests** (extend the matrix, not skip it).
10. **New visibility scopes require resolver policy tests** (same).

**Cross-reference:** этот чеклист каноничен для ревью PR; на него явно ссылаются [**Hard invariants: Recruitment, HR, Document Hub**](invariants-recruitment-hr-document-hub.md) (раздел *AI Agent Notes*), чтобы агенты и люди применяли **один** набор правил, а не расходящиеся трактовки ADR vs invariants.

---

## 11. Acceptance test scenarios (implementation criteria)

These scenarios define **expected behavior** as the resolver and policies land; they are **acceptance / regression** targets for engineering and QA (and for AI-assisted review: “does this PR move us toward or away from these?”).

| # | Scenario | Expected |
|---|----------|----------|
| A | Candidate card is open, but `X-Own-Company-Id` does not match the candidate’s pinned workspace | **Documents summary (and list) must not return 404** solely for that mismatch; workspace affects **slice / placement**, not owner authorization. |
| B | Recruiter in recruitment context | Sees **recruitment-visible** docs; does **not** see **HR-only** documents without an explicit policy path. |
| C | HR after handoff to employee | Sees **transferred / linked employee** documents per policy, not a second copy of blobs. |
| D | Transport / fleet context | Sees **only compliance-relevant** documents (narrow visibility), not the full personal dossier unless policy allows. |
| E | Finance context | Sees **finance-related** documents; does **not** see unrelated personal driver documents **without** a policy that grants them. |
| F | Document under process lock | **Cannot delete or replace** (or other destructive actions) **without** an allowed transition / override recorded in policy. |
| G | File version / attachment | A file version **must not** become downloadable or listable if the **parent document** is not accessible in the resolved context (file ⊑ document visibility). |

**Note:** Rows **B–G** depend on policies and locks existing in code; until Phase 2–4 land, tests may be **skipped or marked `@pytest.mark.xfail`** with a ticket reference — the table remains the **contract** they must eventually satisfy.

---

## 12. Future architecture — non-normative

Future iterations may evolve `DocumentAccessResolver` into a broader policy evaluation layer, but this is **explicitly not required** for Phase 1–2.

**Potential future building blocks:**

- capability-based access;
- policy evaluation graph;
- process-state-aware permissions;
- document obligations;
- redacted external views;
- context-dependent required documents;
- policy test matrix across modules.

This section is **directional only**. Implementation must first complete **resolver foundation**, **API migration**, and **acceptance scenarios** from **§6** and **§11**.
