# HostFlow Platform Canon v1

**Status:** canonical (L1 — **supreme platform constitution**).  
**Owner:** Product + Platform UX + Frontend Architecture.  
**Audience:** design, frontend, backend, AI agents, all module teams.

**Unifies:** visual language · interaction language · interface architecture.

**Catalog (development entry point):** [`hostflow-platform-catalog.md`](hostflow-platform-catalog.md)  
**Build order:** [`ui-primitives-roadmap.md`](ui-primitives-roadmap.md)  
**Product domain (separate):** [`ui-constitution-v1.md`](ui-constitution-v1.md)

---

## §0.0 Phase 0 — complete

Platform Canon, Interaction Rules, and Platform Catalog are **frozen**. Change rarely — only when a Reference primitive exposes a real gap.

**Active work:** Phase 2 — **Entity Model + Universal Entity Workspace Canon**. Detail Rail / Table are projections only — see [`hostflow-entity-workspace-v1.md`](hostflow-entity-workspace-v1.md) §0.

---

## §0. The supreme rule

> **Any interface change is made in the canon first — only then in a module.**

If a button, table, selection rule, rail behavior, or keyboard shortcut changes:

1. Update **Platform Canon** (this document) or the relevant child canon spec.
2. Update the **platform primitive** or **interaction rule** implementation.
3. Modules inherit automatically — they supply **data, actions, permissions only**.

**Forbidden:** module-specific interaction behavior, module-specific layout geometry, module-specific UI elements without canon extension proof.

**Information architecture:** one **Entity Model** per resource type; Collection (table), Detail Rail, and Entity Workspace are **projections** — see Catalog §0.A. Do not add fields to table or rail without updating the model and projection flags.

This discipline is what makes «change one element → change everywhere» real.

---

## §1. What HostFlow is building

> **HostFlow is not a CRM. It is an operational system with one platform language.**

Not «UI Platform». Not «Design System». Not «Interaction Guidelines».

**Platform Canon** — the single constitution for how the product looks, behaves, and is composed.

Modules (Recruitment, Sales, HR, Fleet, Finance) **configure** the platform. They do not **design** interfaces.

---

## §2. Platform stack (four layers)

```text
Layer 1 — Layout System          grid, spacing, AppShell zones
Layer 2 — UI Primitives          Data Table · Detail Rail · Timeline · Contacts · …
Layer 3 — Compositions           Header · Summary · Navigation · Context Rail · Action Bar
Layer 4 — Workspaces           Collection · Entity · Application · Process
```

Entity Model sits **under** Layer 2 — all surfaces project from it. See [`hostflow-entity-model-v1.md`](hostflow-entity-model-v1.md).

---

## §3. The five layers (strict order)

Build and discuss bottom-up. Each layer depends on the one below.

```text
Foundation           grid, spacing, typography, color, radius, motion, icons, shadows
       ↑
Interaction Rules    how the system behaves — platform-wide, not per component
       ↑
Entity Model         passport sections + field projection flags (Phase 2.1)
       ↑
Primitives           Button, Table, Detail Rail, Timeline, Documents, …
       ↑
Compositions         Header, Summary, Navigation, Context Rail, Toolbar, …
       ↑
Workspaces           Collection · Entity · Application · Process
```

| Layer | Owns | Never owns |
|-------|------|------------|
| **Foundation** | Visual tokens (ADR-011) | Module semantics |
| **Interaction Rules** | Click, selection, navigation, editing, action tiers, keyboard | Component markup |
| **Entity Model** | Object passport, projection flags, process state vocabulary | UI layout |
| **Primitives** | One Table, one Detail Rail, one Timeline — variants only | Module names, custom geometry |
| **Compositions** | Header, Summary, Navigation, Context Rail assemblies | Business logic |
| **Workspaces** | Zone layout + config slots | Custom screens / cards |

**Interaction Rules** sit **above** Primitives because behavior is canon **before** any component implements it. Primitives **enforce** rules; they do not invent them.

Full rules: [`hostflow-interaction-rules-v1.md`](hostflow-interaction-rules-v1.md).

---

## §3. What changes per module

| Changes | Never changes |
|---------|----------------|
| Data (fields, entities) | Foundation tokens |
| Available actions | Interaction Rules |
| Access rights | Primitive semantics |
| Section visibility (enable/disable) | Composition geometry |
| Labels, semantic roles | Workspace zone layout |

> **Only data, actions, and permissions change. Not layout. Not behavior. Not interaction logic.**

---

## §4. Core platform laws

### §4.1 No screens

> **There are no screens. There are compositions of primitives.**

### §4.2 No module in primitives

> **No UI primitive knows which module it serves. It knows only the data contract.**

### §4.3 Workspace is not canon

> **Workspace is a composition — not a canon itself.**

### §4.4 Primitive extension rule

> **Forbidden to create a new UI element until an existing Primitive cannot be extended.**

### §4.5 Interaction rule extension

> **Forbidden to add module-specific click, keyboard, or selection behavior. Extend Interaction Rules canon first.**

---

## §5. Flows — two modes of work

The platform is designed around **Flows** (continuous movement), not screens.

| Flow | Pattern |
|------|---------|
| **Decision Flow** | List → Select → Rail → Action → Next object |
| **Entity Flow** | Entity Workspace → Edit → Save → Return (same list context) |

| Intent | Gesture | Surface | When |
|--------|---------|---------|------|
| **Decision** | Row click | **Detail Rail** | Action fits Decision Flow |
| **Entity** | Primary Entity Link | **Entity Workspace** | **Only when Decision Flow is exhausted** |

**Boundary test for every action:** *Can this be done in Decision Flow?*  
Yes → Rail. No → Entity Flow.

**Context Rail** (Entity Flow) ≠ **Detail Rail** (Decision Flow). Same visual language; different contracts.

---

### §4.6 Composition rule (strict)

> **Forbidden to create a new Composition if it requires creating a new Primitive.**

Extend the primitive first. Compositions **assemble** — they are not designed.

### §4.8 Flow Break = bug

> **Any interruption of continuous Flow is a platform bug — not only code exceptions.**

Work unit: **Flow Break** (see Catalog §0, [`decision-flow-breaks-log.md`](decision-flow-breaks-log.md)).  
Phase 1: pass Decision Flow on Candidates, then Sales — zero open breaks.

### §4.9 Development filters

1. **Which Flow Break does this close?**  
2. **Which Flow does this improve?** If unclear → defer.

See [`hostflow-platform-catalog.md`](hostflow-platform-catalog.md).

---

## §6. Build phases (summary)

| Phase | Status |
|-------|--------|
| **0 — Platform Canon** | **Complete — frozen** |
| **1 — Decision Flow Audit** | **Active** — eliminate Flow Breaks (Candidates → Sales) |
| **2 — Primitives queue + Compositions** | After Phase 1 scenario passes |
| **3 — Workspaces** | Config only — fold together |

Detail: [`ui-primitives-roadmap.md`](ui-primitives-roadmap.md). Catalog §0 — product DoD.

---

## §7. Canon documents — reference only

Do not discuss «candidate UI» or «sales screen». Discuss **canons**:

| Canon | Document |
|-------|----------|
| **Platform Catalog** | `hostflow-platform-catalog.md` — **open this first** |
| **Platform (this)** | `hostflow-platform-canon-v1.md` |
| **Interaction Rules** | `hostflow-interaction-rules-v1.md` |
| **Foundation** | ADR-011 + design tokens |
| **Primitives & Compositions** | `hostflow-interaction-platform-v1.md` |
| **Entity Workspace** | `hostflow-entity-workspace-v1.md` |
| **Table · Rail · Selection** | Interaction Rules §1–§2 + platform code |
| **Documents · Timeline · Search · Filter** | Future primitive specs |
| **Product objects** | `ui-constitution-v1.md` |

---

## §8. PR gate (platform changes)

1. Does this change **behavior**? → Interaction Rules canon first.  
2. Does this change **appearance**? → Foundation / Primitive canon first.  
3. Does this change **layout**? → Composition or Workspace canon first.  
4. Which **phase** is active? Frozen surfaces = bugfix only.  
5. Does a module fork a primitive? → **Reject.**

Platform code paths:

```text
hostflow-frontend/src/platform/
  interaction-rules/   ← behavior canon (constants, hooks)
  selection/           ← selection rule implementation
  data-table/
  detail-rail/
  entity-workspace/
```

---

## §9. Supersedes naming

| Old term | Canon term |
|----------|------------|
| HostFlow UI Platform | Platform Canon (visual + interaction + architecture) |
| HostFlow Interaction Platform | Primitives + Compositions layer spec |
| Candidate card / client card | Entity Workspace |
| Component | **Primitive** (atomic) or **Composition** (assembled) |

[`hostflow-ui-platform-v1.md`](hostflow-ui-platform-v1.md) and [`hostflow-interaction-platform-v1.md`](hostflow-interaction-platform-v1.md) remain as detailed child specs; **this document is the entry point**.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-09 | v4 — Flows; Decision/Entity boundary; Flow filter |
| 2026-07-09 | v3 — Phase 1 = Decision Workspace Reference Scenario |
| 2026-07-09 | v1 — Platform Canon; five layers; supreme rule |
