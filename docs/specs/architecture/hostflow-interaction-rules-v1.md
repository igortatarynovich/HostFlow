# HostFlow Interaction Rules v1

**Status:** canonical (L1 — Platform Canon, Layer 2).  
**Owner:** Product + Platform UX + Frontend Architecture.  
**Parent:** [`hostflow-platform-canon-v1.md`](hostflow-platform-canon-v1.md)  
**Implementation:** `hostflow-frontend/src/platform/interaction-rules/`

---

## §0. Definition

> **Interaction Rules define how the system behaves — platform-wide, independent of any single component.**

Behavior is canon **before** Primitives implement it.  
If behavior changes → update **this document first**, then platform code, then modules inherit.

**Not owned here:** visual tokens (Foundation), block layout (Compositions), zone geometry (Workspaces).

---

## §1. Click rules

| Gesture | Result | Scope |
|---------|--------|-------|
| **Click row** (not entity link, not checkbox) | Open / update **Detail Rail** via Selection Model | All collection surfaces |
| **Click Primary Entity Link** | Navigate to **Entity Workspace** | All tables, cards, search results |
| **Click Secondary Entity Link** | Navigate to linked entity's workspace | Same row / card |
| **Double-click** | **Forbidden** — no platform surface uses double-click | Entire platform |
| **Click checkbox** | Toggle bulk selection only — does not open rail | All tables with bulk |

**Event propagation:** Entity links call `stopPropagation()` — link click never triggers row click.

**Same rules apply:** table rows, kanban cards, calendar items, search results, notification items.

---

## §2. Keyboard rules

| Key | When focus on collection row | Result |
|-----|------------------------------|--------|
| **Enter** | Active / highlighted row | Open / focus **Detail Rail** for that row |
| **Cmd+Enter** (macOS) / **Ctrl+Enter** (Windows/Linux) | Active row | Open **Entity Workspace** (Primary link target) |
| **Escape** | Detail Rail open | Close Detail Rail (unless pinned — see §3) |
| **Arrow Up / Down** | Collection has focus | Move active row; update rail if open and not pinned |
| **Double-click** | Anywhere | **Not used** |

Rail navigation when open and not pinned:

| Key | Result |
|-----|--------|
| **Arrow Up / Down** | Previous / next entity in current ordered list |
| **Escape** | Close rail |

**Forbidden:** module-specific keyboard shortcuts that contradict this table without canon amendment.

---

## §3. Selection rules

| Rule | Behavior |
|------|----------|
| **Single focus** | At most one **active** row/card at a time (highlight) |
| **Bulk selection** | Only via checkboxes — separate from active row |
| **Active highlight** | Same visual treatment on every collection surface |
| **Rail target** | `railEntityId` follows active row unless **pinned** |
| **Pin** | When pinned, row navigation does not change rail content |
| **Filter / sort change** | If `railEntityId` still in `orderedIds` → **rail stays open** |
| **Entity leaves view** | Rail closes (configurable; default: close) |
| **Bulk bar** | Visible when ≥1 checkbox selected; does not replace active row semantics |

**Owner:** `platform/selection/` — Universal Selection Model.

---

## §4. Navigation rules

| Rule | Behavior |
|------|----------|
| **Back from Entity Workspace** | Returns to **same collection** (same route + query state) |
| **List state preserved** | Filters, sort, scroll position, saved view — restored on return |
| **Same row** | After closing Entity Workspace, active row is the entity user came from |
| **Breadcrumb** | Entity Workspace header shows path back to collection |
| **Prev / next in Entity Workspace** | Moves within **current collection context** (same filter/sort order) |
| **Deep link** | Direct URL to entity opens Entity Workspace; back goes to module default list if no referrer |

**Forbidden:** navigation that drops filter state without user intent (e.g. hard redirect to unfiltered list).

---

## §5. Editing rules

| Surface | Editable | Notes |
|---------|----------|-------|
| **Data Table** | **No** inline edit | Actions trigger dialogs or navigate to workspace |
| **Detail Rail** | **No** | Read-only + quick actions only (`data-detail-rail-readonly="true"`) |
| **Entity Workspace — Content** | **Yes** | Primary editing surface |
| **Entity Workspace — Summary** | Configurable | Inline edit only if canon primitive allows |
| **Context Rail** | **No** | Actions and task completion only |

> **Detail Rail never edits data. Entity Workspace edits. Table does not edit.**

---

## §6. Action rules

Applies to: Detail Rail, Context Rail, Entity Header, Toolbars, Bulk bar.

| Tier | Count | Presentation |
|------|-------|--------------|
| **Primary** | **Exactly one** dominant action when any action exists | Large / filled button |
| **Secondary** | **2–4** frequent actions | Compact buttons |
| **More** | Everything else | Overflow menu |

**Forbidden:**

- Two primary buttons of equal weight
- Module-specific action tier layout
- Hiding destructive actions without More menu path

**Contract:** `DetailRailActionsTier`, `ContextRailModel.actions` — same tier shape everywhere.

---

## §7. Notification & feedback rules (summary)

| Event | Rule |
|-------|------|
| **Action success** | One Notification primitive — success type |
| **Action failure** | One Notification — error type; rail/table state unchanged unless action committed |
| **Optimistic update** | Forbidden in Detail Rail; Entity Workspace may use per primitive spec |
| **Loading** | Skeleton primitive — same pattern everywhere |

---

## §8. Enforcement

### §8.1 Code

`platform/interaction-rules/` exports canonical constants and types.  
Hooks (`useSelectionModel`, future `useInteractionKeyboard`) implement rules — modules call hooks, never reimplement.

### §8.2 PR checklist

- [ ] New click handler — does it match §1?
- [ ] New keyboard handler — does it match §2?
- [ ] Selection change — goes through Selection Model?
- [ ] Editable field in rail — **reject**
- [ ] Second primary action — **reject**
- [ ] Double-click handler — **reject**

### §8.3 Testing

Interaction Rules are platform-level acceptance criteria for Phase 1 DoD and all collection pilots.

---

## §9. Relationship to primitives

```text
Interaction Rules (this doc)     ← WHAT must happen
        ↓
Selection Model, DataTable,     ← HOW it is implemented
DetailRail, keyboard hooks
        ↓
Module adapters                  ← data + actions only
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | v1 — click, keyboard, selection, navigation, editing, action tier rules |
