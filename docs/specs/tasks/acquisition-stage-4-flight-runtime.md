# Acquisition Stage 4 — Flight Runtime

**Status:** Active — **PR-2 in progress** (Campaign + Endpoint CRUD hardening)  
**Canon:** [ADR-024](../architecture/ADR-024-acquisition-campaigns-intake-routing.md) §14 · §14.1  
**Depends on:** Stage **3E** complete ✅ (Activity Timeline PR #130–#133) · Stage 4 **PR-1** ✅ (#136)  
**Parents:** [Stage 3E — Activity Timeline](acquisition-stage-3e-activity-timeline.md) · Epic P / 3D ✅  
**Branch:** `feat/acquisition-stage-4-pr2-crud-hardening` · worktree `/opt/HostFlow-wt/acq-stage-4`  
**Deferred (not Stage 4):** [acquisition-stage-3e-deferred.md](acquisition-stage-3e-deferred.md)  
**Next horizons:** Stage 5 Optimization · Stage 6 Analytics (see ladder below; not opened)

> **Operations layer** for Acquisition — Campaign / Flight day-to-day control.  
> Uses Stage 3E Activity Timeline as **observability infrastructure**; does **not** redefine it.

---

## Acquisition maturity ladder

| Stage | Layer | Verb | Status |
|-------|--------|------|--------|
| **3E** | Observability | See | **DONE** (#130–#133) |
| **4** | Operations | Control | **This epic (PR-2 active)** |
| **5** | Optimization | Improve | Future horizon |
| **6** | Analytics | Decide | Future horizon |

Normative detail: [ADR-024 §14.1](../architecture/ADR-024-acquisition-campaigns-intake-routing.md).

---

## PR sequence

| PR | Scope |
|----|--------|
| **PR-1** | Backend Flight Runtime Contract (commands + coupling + metadata) — ✅ #136 |
| **PR-2** | Campaign + Endpoint operational CRUD hardening — **active** |
| **PR-3** | Runtime Read API + Live Intake Monitor backend |
| **PR-4** | Operations UI |
| **PR-5** | Production hardening / provider-runtime gaps |

---

## PR-1 — Backend Flight Runtime Contract (locked)

### Flight transition matrix (existing only)

```text
planned → active      → FlightStarted   (launch)
active  → paused      → FlightPaused    (pause)
paused  → active      → FlightResumed   (resume)
active  → completed   → FlightCompleted (complete)
```

**Cancel deferred** — requires new Flight status, matrix, Activity event, Campaign impact, routing eligibility, re-launch rules, migration. Not in PR-1.

### Campaign coupling (PR-1 only)

| Command | Flight | Campaign status | Campaign Activity |
|---------|--------|-----------------|-------------------|
| launch | → active | → `active` | `CampaignActivated` if changed |
| pause | → paused | → `paused` | `CampaignPaused` if changed |
| resume | → active | → `active` | `CampaignActivated` if changed |
| complete | → completed | **unchanged** | none |

### IN

- Canonical command service: `backend/app/acquisition/flights/runtime_commands.py`
- Flight get/list + metadata PATCH (`name`, `starts_at`, `ends_at`)
- HTTP: `POST …/flights/{id}/launch|pause|resume|complete`
- Lifecycle status **forbidden** on Flight PATCH
- Idempotent retry via existing lifecycle `source_event_id`
- Permissions: same campaigns `_WRITE` / `_READ`
- Activity via `append_activity_event` / `transition_flight_status` only
- Tests: coupling, illegal transition, rollback, HTTP, idempotent retry

### OUT

- UI · Live Intake Monitor · metrics · budget automation · provider APIs · scheduling · optimization  
- New Acquisition pipelines · multi-flight · Endpoint redesign · `FlightFailed` invent · **Cancel**  
- Inventing Campaign completed lifecycle on Flight complete

### Implementation bias

Wrap `transition_flight_status` — do not fork a second Flight status writer.

---

## Epic in scope (full Stage 4)

1. Campaign CRUD (operator-facing)  
2. Flight CRUD  
3. Endpoint Management  
4. Launch / Pause / Resume (+ Complete in PR-1)  
5. Live Intake Monitor  
6. Basic Metrics (submissions, leads, candidates, CPL)  
7. Runtime actions (operator controls that emit Timeline events via existing append contract)

## Out of scope (initial Stage 4)

- Stage 5 Optimization (auto pause/resume policies, AI recommendations, anomaly-driven actions as a product suite)  
- Stage 6 full analytics / Intelligence suite (ROI, cohort compare, strategic dashboards)  
- Multi-Flight wave compare (V2)  
- CampaignTemplate catalog  
- Provider Ads Manager replacement  
- Redefining Activity Timeline schema or public append/list contract  
- Cancel Flight (deferred domain decision)

---

## PR-2 — Campaign + Endpoint operational CRUD hardening (locked)

Hardening over existing 3A/3B/PR-1 surfaces — **not** greenfield CRUD.

### IN

1. **Campaign status discipline** — lifecycle status forbidden on `PATCH /campaigns/{id}` (metadata only: name, description, goal_type, primary_kpi). Mirror Flight PR-1.
2. **`CampaignCreated`** — emit on `create_campaign` (same txn as `FlightCreated`), deterministic `source_event_id`.
3. **Campaign terminal commands** — `POST …/complete` → `completed` + `CampaignCompleted`; `POST …/archive` → `archived` + `CampaignArchived`. Idempotent retry. Does **not** auto-complete/cancel Flight (Flight complete remains PR-1 command; Cancel deferred).
4. **Endpoint binding HTTP parity** — `PATCH …/flights/{flight_id}/forms/{link_id}` and `…/intake-sources/{link_id}` (service already accepts `flight_id`).
5. Tests for status PATCH forbidden, CampaignCreated, complete/archive + events, flight-scoped link PATCH.

### OUT

- Operations UI / frontend client completeness (PR-4)  
- Runtime Read API + Live Intake Monitor (PR-3)  
- Multi-Flight create · Flight Cancel · unified Endpoint entity redesign  
- IntakeSourceProfile / Binding SoT CRUD outside Acquisition  
- Activity on every target/goal metadata edit  
- Provider runtime · metrics · optimization

### Campaign status writers (after PR-2)

| Path | Status effect |
|------|----------------|
| `create_campaign` | → `draft` + `CampaignCreated` |
| Flight launch / resume (PR-1) | → `active` + `CampaignActivated` if changed |
| Flight pause (PR-1) | → `paused` + `CampaignPaused` if changed |
| `POST …/complete` | → `completed` + `CampaignCompleted` |
| `POST …/archive` | → `archived` + `CampaignArchived` |
| `PATCH …` | **no status** |

---

## History

- 2026-07-21: Opened as **queued** epic — Stage 3E = observability only; Stage 4 = operations (Flight Runtime).  
- 2026-07-21: Linked to maturity ladder — Operations → then Optimization (5) → Analytics (6).  
- 2026-07-21: Stage 3E DONE; Product Track → Stage 4; worktree opened.  
- 2026-07-21: **PR-1 locked** — Flight Runtime backend contract; Cancel deferred; Campaign sync only on launch/pause/resume.  
- 2026-07-21: **PR-1 merged** (#136).  
- 2026-07-23: **PR-2 locked** — Campaign status discipline, CampaignCreated, complete/archive commands, Endpoint PATCH parity.
