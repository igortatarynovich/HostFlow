# PRIMITIVES_BENCHMARK

Status: Complete  
Date: 2026-05-29  
Input: `PRIMITIVES_INVENTORY.md`  
Scope: **Badges + Chips only** — no Select / Button / Input detail.  
Purpose: classify Badge and Chip implementations as **Candidate**, **Legacy**, or **Deprecated** for future `STATUS_BADGE_V1` and `CHIP_V1`.

## Question Answered

> Какие Badge и Chip реализации становятся Candidate / Legacy / Deprecated для будущих STATUS_BADGE_V1 и CHIP_V1?

## Governing Rules

| Status | Meaning | New code | Existing code |
|---|---|---|---|
| **Candidate** | Default for new work | Required | Keep |
| **Legacy / Adapt** | Allowed; migrate on touch | Discouraged | Keep until refactored |
| **Deprecated** | Forbidden pattern | Forbidden | Migrate with backlog |

**Locked decisions (this benchmark):**

1. `STATUS_BADGE_V1` is **semantic-first**, not color-first — `success`, `warning`, `danger`, `info`, `neutral`, `brand` (aligned with `FOUNDATION_V1`).
2. `CHIP_V1` has a **limited behavior variant set** — no new local chip implementations.

---

## 1) Badges / Status

### Classification

| Current implementation | Uses | Decision | Rationale | Maps to `STATUS_BADGE_V1` |
|---|---:|---|---|---|
| `NextActionBadge` | 7 JSX | **Candidate** | DTO-driven, structured priority semantics; best reference API | Priority → semantic mapping (`danger`/`warning`/`info`/`neutral`) |
| `StageTag` | 10 JSX | **Legacy / Adapt** | Real pipeline usage; 30 color keys must collapse to semantics | Stage code → semantic role (not per-stage color) |
| `DocumentStatus` | 6 JSX | **Legacy / Adapt** | 4 severities already semantic-ish; merge into status badge | `ok`→success, `warn`→warning, `bad`→danger, default→info |
| `.badge` CSS (static) | 75 | **Legacy / Adapt** | Shared class, no semantics; wrap with semantic badge | `neutral` default |
| Inline pills (`rounded-md px-2`, `rounded-full border px-2`) | 119 | **Legacy / Adapt** | Ad-hoc admin/HR/candidate pills; migrate on touch | Map local intent to nearest semantic |
| Per-stage / per-hue color maps | 30+ keys | **Deprecated** | Color-first model; conflicts with `FOUNDATION_V1` | Replace with semantic tokens |
| Deprecated color palettes in badges | 16 `StageTag` keys | **Deprecated** | `green`, `red`, `indigo`, `yellow`, `orange`, `purple`, `sky`, `teal`, `violet` families | → `FOUNDATION_V1` allowed families |

### Semantic-first model (pre-decision for V1 Draft)

`STATUS_BADGE_V1` must expose semantics, not palette slots:

| Semantic | Use | Foundation source |
|---|---|---|
| `success` | positive / complete / employed | `color-success` |
| `warning` | attention / pending / at-risk | `color-warning` |
| `danger` | rejected / error / blocked | `color-danger` |
| `info` | informational / in-progress | `color-info` |
| `neutral` | default / unknown / closed | `color-neutral` |
| `brand` | active / contacted / pipeline-active | `color-brand` |

**Forbidden in new status badges:** `bg-green-100`, `bg-red-100`, `text-emerald-800` as design API. Palette mapping lives in one config layer only.

### `StageTag` adaptation rule

| Today | Benchmark decision |
|---|---|
| 30 stage → color entries | **Deprecated** as canon |
| Stage label display | **Legacy / Adapt** — keep component until semantic map exists |
| `size: sm \| md` | **Candidate** size model (carry to V1) |

Stage-to-semantic mapping is a **product decision** in `STATUS_BADGE_V1` draft — not re-decided here. Benchmark only locks: no new color keys.

### `NextActionBadge` as reference

| Priority (current) | Proposed semantic |
|---|---|
| Critical / overdue | `danger` |
| High | `warning` |
| Normal | `info` |
| Low / none | `neutral` |

Candidate for first `STATUS_BADGE_V1` adapter — not a second badge system.

### Migration priority (Badges)

| Priority | Action | Effort |
|---|---|---|
| P0 | Stop new inline status pills in changed files | Policy |
| P1 | Map `StageTag` deprecated palettes → allowed semantics | Medium |
| P2 | Merge `DocumentStatus` into shared status badge | Low |
| P3 | Replace inline pills on touch | Ongoing |

---

## 2) Chips

### Classification

| Variant / implementation | Uses | Decision | Rationale | Maps to `CHIP_V1` |
|---|---:|---|---|---|
| Dismissible chip (`FilterBadges`) | 21 refs | **Candidate** | Clear behavior; primary filter UX in candidates | `behavior="dismissible"` |
| Selectable chip (`CandidatesQuickViewsBar`, `MultiSelectChips`) | 15 refs | **Candidate** | Toggle/selection UX; same primitive, different state | `behavior="selectable"` |
| Action chip (`NbaNextActionsChips`) | 3 refs | **Candidate** (or separate later) | Navigation/action affordance; may split if interaction model diverges | `behavior="action"` — review in V1 Draft |
| Static label chip (read-only) | implicit in badges | **Candidate** | Base variant for non-interactive chips | `behavior="static"` |
| Inline custom chips (ad-hoc `chip` patterns) | 11 refs | **Deprecated** | Unowned local implementations | → `CHIP_V1` variant |
| New local chip implementations | — | **Deprecated** | Forbidden in new code | Use `CHIP_V1` |

### `CHIP_V1` behavior set (locked at benchmark)

| Behavior | Interactive | States | Reference implementation |
|---|---|---|---|
| `static` | No | default | base chip |
| `dismissible` | Yes (remove) | default | `FilterBadges` |
| `selectable` | Yes (toggle) | default, selected | `CandidatesQuickViewsBar` |
| `action` | Yes (navigate/trigger) | default, hover | `NbaNextActionsChips` |

**Maximum 4 behaviors.** No fifth local pattern without governance.

### Action chip — open point for V1 Draft

Benchmark classifies `action` as **Candidate**, with note: if action chips need distinct a11y/keyboard contract, V1 Draft may promote to `ActionChip` sibling — not a second benchmark pass.

### Migration priority (Chips)

| Priority | Action | Effort |
|---|---|---|
| P0 | No new inline chip markup in PR diffs (policy until enforcement) | Policy |
| P1 | Extract `FilterBadges` → `CHIP_V1` dismissible | Medium |
| P2 | Extract `CandidatesQuickViewsBar` → `CHIP_V1` selectable | Medium |
| P3 | `NbaNextActionsChips` → action variant | Low |

---

## 3) Queued (not benchmarked in this document)

Per scope lock — sufficient inventory exists; classification deferred to later benchmark pass:

| Family | Priority | Future artifact | Status |
|---|---|---|---|
| Selects | P1 | `SELECT_V1` | Queued |
| Buttons | P1 | `BUTTON_V1` | Queued |
| Inputs | P2 | `INPUT_V1` | Queued |
| Checkbox / Radio / Toggle | P2 | defer | Queued |

---

## 4) Decision Log

| # | Decision | Evidence |
|---|---|---|
| D1 | `NextActionBadge` = Candidate reference for status badges | Structured API, inventory P0 |
| D2 | `StageTag` = Legacy/Adapt, color map = Deprecated | 30 hues vs 6 semantics |
| D3 | `DocumentStatus` = Legacy/Adapt | 4 severities map cleanly to semantics |
| D4 | Inline pills = Legacy/Adapt | 119 uses, no API |
| D5 | Deprecated badge palettes = Deprecated | `FOUNDATION_V1` conflict |
| D6 | STATUS_BADGE_V1 = semantic-first | Foundation chain alignment |
| D7 | Dismissible + selectable chips = Candidate | Clear behavior owners |
| D8 | Action chip = Candidate (split TBD in V1 Draft) | Low usage, distinct UX |
| D9 | Inline custom chips = Deprecated | UI debt pattern |
| D10 | Select/Button/Input out of scope | User scope lock |

---

## 5) What This Benchmark Does NOT Do

- Does not write `STATUS_BADGE_V1` or `CHIP_V1` drafts.
- Does not define stage→semantic mapping table (V1 Draft).
- Does not classify Select, Button, Input families.
- Does not execute migrations.

---

## Output to Next Step

Next artifacts (in order):

1. **`STATUS_BADGE_V1_DRAFT`** (Layer 3) — semantic badge spec + stage map.
2. **`CHIP_V1_DRAFT`** (Layer 2 primitive) — 4 behavior variants.
3. **`PRIMITIVES_V1_DRAFT`** — partial draft covering Badge + Chip only; other families queued.

Chain:

| Artifact | Status |
|---|---|
| `PRIMITIVES_AUDIT.md` | ✅ |
| `PRIMITIVES_INVENTORY.md` | ✅ |
| `PRIMITIVES_BENCHMARK.md` | ✅ This document |
| `STATUS_BADGE_V1_DRAFT` | ✅ Draft |
| `CHIP_V1_DRAFT` | ✅ Draft |
| Implementation + lock | ← Next |
