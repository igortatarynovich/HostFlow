# Document UI Status Badges — platform capability canon (P0)

**Status:** Accepted (architecture canon). **Implementation:** P0 canon open; P1 consumer layer in progress.  
**Hierarchy:** L2 operating canon — presentation layer. **Read-only projection** of `document_runtime_v1`.  
**Owner:** Architecture canon + platform core team.

**Opened:** 2026-06-24 — immediately after **Document Expiry Notifications v1 closed** ([`document-expiry-notifications-p0.md`](document-expiry-notifications-p0.md) §20).

**Next implementation step:** P1 — `runtimeBadgePresentation` mapper + wire DocumentCard, Document Hub checklist, Candidate Docs rail/panel.

**Related canon (must stay consistent):**

| Document | Relationship |
|----------|--------------|
| [`document-runtime-engine-p0.md`](document-runtime-engine-p0.md) | **Single upstream source** — `document_runtime_v1` + delivery contract |
| [`document-expiry-notifications-p0.md`](document-expiry-notifications-p0.md) | Notification events consume runtime; Notification Center badges are **out of P1 scope** |
| [`ADR-009`](../architecture/ADR-009-document-hub-platform-layer.md) | Document Hub owns instances; badges do **not** re-evaluate lifecycle |
| [`requirement-rules-engine-p0.md`](requirement-rules-engine-p0.md) | Requirement Engine defines *what is required*; badges show *instance runtime state* |

---

## 1. Purpose

**Document UI Status Badges** answer:

> Given canonical `document_runtime_v1`, what label, color, and secondary indicator should the UI show — without deciding lifecycle, expiry, or requirement satisfaction?

Badges are a **read-only projection**. They do not compute status, compare dates, or derive buckets from owner summary.

| Responsibility | Detail |
|----------------|--------|
| **Badge vocabulary** | Fixed v1 set mapped from runtime fields |
| **Presentation mapper** | Pure function: `document_runtime_v1` → badge label + semantic styling |
| **Consumer wiring** | DocumentCard, Hub checklist, Candidate Docs rail/panel |
| **Secondary indicator** | `satisfies_requirement` → icon/outline only — **not** a separate badge type |

**Main canon (non-negotiable):**

| Layer | Question |
|-------|----------|
| **Document Runtime Engine** | What is lifecycle + expiry state? |
| **Document UI Status Badges (this)** | How does the UI *display* that state? |
| **Notification Center** | How are expiry *events* listed? (separate track — not P1) |

---

## 2. Non-goals (P0)

Document UI Status Badges P0 is **not**:

| Non-goal | Where it belongs instead |
|----------|--------------------------|
| Re-evaluating expiry / workflow | Document Runtime evaluator |
| Owner summary bucket logic | Legacy `owner_summary.py` (strangler) |
| Notification event presentation | Notification Center read UI |
| Status edit controls (dropdown, approve/reject) | Document Hub workflow UX — uses hub `status`, not badge mapper |
| New backend evaluator fields | Document Runtime Engine v1 (frozen) |
| i18n product copy redesign | Presentation layer follow-up |

**P0 rule:** If the UI computes `expired`, `expiring_soon`, or `approved` from dates or legacy status heuristics — it violates this canon.

---

## 3. Source of truth

### 3.1 Allowed (only)

**Document Runtime Delivery Contract** → `document_runtime_v1` on:

- Each document instance payload (`document_runtime` on `DocumentOut`)
- Hub checklist runtime items (`document_runtime.items[]` / `runtimeItems`)

Canonical runtime fields used by the badge mapper:

| Field | Role |
|-------|------|
| `workflow_status` | uploaded, pending_review, approved, rejected, missing, … |
| `expiry_status` | valid, expiring_soon, expired, no_expiry |
| `runtime_signal` | Dominant operational signal when present |
| `satisfies_requirement` | Secondary indicator only |

### 3.2 Forbidden as badge source

| Forbidden source | Why |
|------------------|-----|
| `expires_on` / `expire_date` / `expires_at` directly | Expiry dimension owned by runtime evaluator |
| Owner summary buckets (`ready_types`, `problematic`, `expiring_soon[]`) | Legacy aggregation — drift risk vs runtime |
| Readiness fragments / checklist counters | Downstream projections |
| Frontend date math (`daysUntil`, `Date.parse` for badge) | Duplicates evaluator |
| Hub `DocumentStatus` enum heuristics for badge display | Workflow storage ≠ runtime projection |

---

## 4. Badge vocabulary v1

| Runtime condition | Badge |
|-------------------|-------|
| approved + valid (satisfies or signal null, not expired) | `approved` |
| uploaded / pending_review / pending_verification | `pending` |
| rejected | `rejected` |
| expired | `expired` |
| expiring_soon | `expiring_soon` |
| missing | `missing` |

**Secondary indicator:** `satisfies_requirement === true` may add icon/outline/secondary styling. It must **not** become a separate badge type (e.g. no `satisfied` badge).

**Precedence (mapper):** missing → rejected → expired → expiring_soon → pending → approved.

---

## 5. Hard rules (UI)

### 5.1 Forbidden in badge code paths

- Computing `expired` from dates
- Computing `expiring_soon` from dates or thresholds
- Computing `approved` from hub status rank / `READY_STATUSES`
- Comparing expiry dates for badge display

### 5.2 Legacy helpers

Any code named or behaving like:

- `isExpiringSoon(...)`
- `isExpired(...)`
- `primaryStatus(...)` **when used for badge display**

Must become a **thin adapter** to `runtimeBadgePresentation`, or be **removed** from badge paths.

Workflow edit controls may continue to read hub `status` — that is not a badge.

### 5.3 Single mapper

All P1 consumers call **`runtimeBadgePresentation`** (or its exported helpers). No consumer-local badge mapping.

---

## 6. P1 consumers

| Consumer | P1 | Notes |
|----------|----|-------|
| `DocumentCard` | ✅ | Instance badge + remove duplicate expiring-soon chip when badge covers it |
| Document Hub checklist (`CandidateDocuments` / runtime items) | ✅ | Per-type badge from `runtimeItems` |
| Candidate Docs rail / panel | ✅ | Row status from runtime items, not legacy `expiring_soon[]` buckets |
| Notification Center | ❌ | Uses notification event presentation — separate canon |

---

## 7. P1 acceptance

1. All badges built through `runtimeBadgePresentation`.
2. No local expiry logic in badge code paths.
3. Same `document_runtime_v1` → same badge on DocumentCard, Hub checklist, and Candidate Docs rail.
4. Unit tests cover the mapper (precedence, vocabulary, `satisfies_requirement` indicator).
5. Backend Document Runtime **evaluator unchanged** — API may attach existing `enrich_snapshot_via_contract` output only.

---

## 8. Architecture smell addressed

| Before | After |
|--------|-------|
| Backend computes `document_runtime_v1` | Unchanged |
| Frontend computes status/expiry in places | Badges read runtime only |
| Hub vs Candidate Card drift risk | Single mapper, single runtime source |

---

## 9. Post-P1 (not foundation)

| Track | Scope |
|-------|-------|
| Filter UX alignment | Map status filters to runtime badges where product requires |
| Upcoming deadlines panel | May keep date display for calendar UX — not a status badge |
| v1 closure §20 | After P1 acceptance + tests green |

**Foundation stack (complete upstream):**

```
Field Registry → Entity Profile → Requirement Rules → Document Hub → Document Runtime → Delivery Contract
                                                                                              ↓
                                                                              Document UI Status Badges (this)
```
