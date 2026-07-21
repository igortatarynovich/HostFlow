# Acquisition Stage 3E — Activity Timeline & Runtime Observability

**Status:** Active (Product Track kickoff — canon correction before code)  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §10 · §14 slice **3E**  
**Parents:** Epic P / 3D ✅ · R3.5 Flights dispatch ✅ · Forms Sprint 1–6 ✅  
**Branch (PR-1):** `feat/acquisition-stage-3e-pr1-activity-foundation`

> Closes the **V1 vertical** (3A→3E): operators can observe Acquisition inbound-flow history end-to-end.  
> **Not** C2.4. **Not** full multi-Flight UX / Template catalog (V2).  
> **Not** Flight-centric log. Model = **`AcquisitionActivityEvent`**.

**Supersedes naming:** earlier draft `acquisition-stage-3e-flight-timeline.md` (Flight Timeline) — do not implement that framing.

---

## Why now

Communication foundation (C0–C2.2, C2.3 implemented) is mature enough for daily ops.  
**Product Track** = Acquisition / Flights. The next value jump is **Activity Timeline** — durable, typed history of the inbound demand flow.

```text
Campaign → Flight → Endpoint → Submission → Result → Outcome
                 ↑
     Acquisition Activity Timeline (single store, many views)
```

---

## Product Track vs Engineering Track

| Track | Work | Blocks Product? |
|-------|------|-----------------|
| **Product** (this slice) | Activity Timeline foundation → instrumentation → read API → thin UI | — |
| **Engineering** | Full-repo pytest debt, #127 CI-unblock polish, C2.3 merge rebase | **No** — unless clean deploy / Alembic / new module bootstrap breaks |

C2.4 Scheduling remains **frozen**. C2.3 stays implementation-complete; merge when Engineering Track can land without stopping Product.

---

## Locked architecture (before PR-1)

### Aggregate

**`AcquisitionActivityEvent`** — owned by Acquisition. Describes the full inbound flow, not only Flight lifecycle.

Flight is the **primary operational context** for many events (`flight_id` set), but **not** the owner of the model. Campaign-level, Endpoint-level, and routing events must not be forced onto a Flight or duplicated in parallel journals.

### Canonical fields

| Field | Purpose |
|-------|---------|
| `id` | Internal record id |
| `tenant_id` | Mandatory tenant isolation |
| `campaign_id` | Root flow context |
| `flight_id` | Nullable |
| `endpoint_id` | Nullable |
| `submission_id` | Nullable |
| `result_id` | Nullable |
| `outcome_id` | Nullable |
| `event_type` | Closed catalog type |
| `event_version` | Event contract version |
| `occurred_at` | When the fact happened |
| `recorded_at` | When HostFlow persisted it |
| `actor_type` | `user` / `system` / `automation` / `provider` |
| `actor_id` | Nullable |
| `provider` | Nullable; **never** architecture SoT |
| `source_event_id` | External / retry idempotency |
| `correlation_id` | One business operation |
| `causation_id` | Cause linkage |
| `payload` | Versioned typed data for that `event_type` |

`payload` is **not** a free-text log. User-facing copy is a UI concern.

### Immutability

> **Acquisition Activity Timeline is append-only and immutable.**

Forbidden:

- update / delete of rows  
- mutating `payload`  
- back-dating corrections in place  

Corrections are **new** events (`BudgetChanged`, `EndpointCorrected`, `OutcomeReclassified`, `ProviderStatusCorrected`, …).

Enforcement layers: **no** public update/delete methods on append service or repository interface; DB constraints / grants as appropriate so mutations are not a supported path.

### Timeline ≠ event bus

```text
Domain operation → Domain Event → consumers
                      ├── Activity Timeline projector (audit projection)
                      ├── Automation Engine
                      ├── analytics read models
                      └── notifications
```

- **Timeline** = durable audit / observability projection.  
- **Domain Event / Outbox** = delivery and integration.  

Automation Engine **must not** treat the Timeline table as a queue.  
Where required, domain state change + domain event share one transaction; Timeline projection appends idempotently from that event.

### Single store, many views

One table: `acquisition_activity_events`.

| View | Filter |
|------|--------|
| Flight Activity | `flight_id` |
| Campaign Activity | `campaign_id` |
| Submission trace | `submission_id` |
| Result / Outcome trace | `result_id` / `outcome_id` |

Campaign Timeline is **not** a second aggregate and **not** a copy of Flight rows.

### Provider-agnostic

Meta, TikTok, Google, LinkedIn, Landing Page, API, Referral — same Timeline contract. `provider` is optional metadata only.

### Ownership boundary

Deep-links / ids for Lead, Candidate, Application, Inquiry, etc. **do not** transfer ownership to Acquisition. CRM/Operations objects stay in owning modules (ADR-024).

---

## Event Catalog v0

Names must include the object (`FlightCompleted`, not bare `Completed`).

### Campaign

- `CampaignCreated`
- `CampaignActivated`
- `CampaignPaused`
- `CampaignCompleted`

### Flight

- `FlightCreated`
- `FlightStarted`
- `FlightPaused`
- `FlightResumed`
- `FlightCompleted`
- `FlightFailed`

### Configuration

- `BudgetChanged`
- `AudienceChanged`
- `EndpointChanged`

### Provider lifecycle

- `ProviderSubmissionAccepted`
- `ProviderSubmissionRejected`
- `ProviderStatusChanged`
- `LearningPhaseEntered`
- `LearningPhaseExited`

### Intake pipeline

- `SubmissionReceived`
- `SubmissionNormalized`
- `SubmissionRejected`
- `RoutingCompleted`
- `RoutingFailed`
- `ResultAttributed`
- `OutcomeChanged`

### Business entities (attribution signals, not ownership)

- `LeadCreated`
- `CandidateCreated`
- `DuplicateDetected`

### Automation and monitoring

- `FlightAutoPaused`
- `FlightAutoResumed`
- `SpendAnomalyDetected`
- `DeliveryErrorOccurred`

Catalog may grow only by additive, versioned types — never by free-text `event_type`.

---

## Three responsibilities — separated

| Concern | Owner in 3E | Must not become |
|---------|-------------|-----------------|
| **1. Audit of Acquisition lifecycle** | Activity Timeline (`AcquisitionActivityEvent`) | Command source / message broker |
| **2. Domain events for automations** | Domain Event / Outbox → Automation Engine | Timeline-as-queue |
| **3. Operator UI** | Thin read UI (PR-4 only) | Write path / analytics suite |

Mixing these in one PR or one “Flight Timeline + emit for Automations + UI” slice is **forbidden**.

---

## Implementation split (PR 1–4)

### PR-1 — Activity Foundation

**Includes:**

- `AcquisitionActivityEvent` model + migration (`acquisition_activity_events`)  
- Event Catalog v0  
- Versioned typed payload contracts  
- Immutable append service  
- Idempotency on `source_event_id` (tenant-scoped)  
- `correlation_id` / `causation_id`  
- Internal query repository (no HTTP)  
- Contract tests: immutability, tenant isolation, idempotent append  

**Excludes:**

- HTTP Timeline API  
- UI  
- Mass instrumentation of existing call sites  
- Automation Engine wiring  
- Budget business logic  
- Analytics  

**Branch:** `feat/acquisition-stage-3e-pr1-activity-foundation` (**in progress**).

### PR-2 — Existing Flow Instrumentation

Emit from the existing 3C/3D chain **without a second pipeline**:

- Flight lifecycle  
- Endpoint  
- Submission  
- Routing  
- Result  
- Outcome  
- Lead / Candidate / Duplicate where Acquisition receives a confirmed signal  

Events must be written from the same transaction as the domain change **or** via outbox → projector — not best-effort post-commit fire-and-forget.

### PR-3 — Timeline Read API

- Flight activity  
- Campaign roll-up (filter, not copy)  
- Cursor pagination  
- Filter by type and time  
- Stable order: `occurred_at` + `id`  
- Tenant + RBAC enforcement  

### PR-4 — Thin Operator UI

- Single Activity Timeline surface  
- Grouping + human labels (UI maps `event_type`)  
- Links to related objects  
- Technical details on expand  
- **No** edit/delete  
- **No** charts / full analytics / budget editor  

```text
1. Foundation (model + append + catalog)
2. Instrument existing 3C/3D paths
3. Read API
4. Thin UI last
```

---

## Out of scope (all of 3E)

- Multi-Flight UX / wave compare (V2)  
- CampaignTemplate catalog  
- Forms Builder expansion  
- C2.4 Scheduling  
- Using Timeline as Automation Engine transport  
- Fixing the 657 base-known integration pytest failures (Engineering Track)  
- Weakening Acquisition product contract tests  

---

## Definition of Done (Stage 3E)

- [ ] Single immutable Activity Timeline store (`acquisition_activity_events`)  
- [ ] Events typed + versioned (`event_type` + `event_version` + payload contracts)  
- [ ] Retry / redelivery does not duplicate (`source_event_id` idempotency)  
- [ ] Tenant isolation enforced (app + tests)  
- [ ] Flight and Campaign history from one store without row copies  
- [ ] Existing 3C/3D chain instrumented without a second pipeline  
- [ ] Timeline is **not** used as Automation Engine queue  
- [ ] Read API available (PR-3)  
- [ ] Operator can inspect history in minimal UI (PR-4)  
- [ ] Clean PostgreSQL migration path  
- [ ] Acquisition contract suites green; no new SPA `/app` literals; no cross-module ownership breaks  
- [ ] Base-known 657 legacy failures are **not** a Product blocker  
- [ ] ADR-024 3E marked DONE; V1 vertical closed  

---

## History

- 2026-07-21: Opened as Product Track (Flight Timeline draft).  
- 2026-07-21: **Canon correction** — `AcquisitionActivityEvent`; Timeline ≠ event bus; PR 1–4; provider-agnostic; single store / many views. Filename → `acquisition-stage-3e-activity-timeline.md`.
