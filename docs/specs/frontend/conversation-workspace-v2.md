# Conversation Workspace v2

**Status:** Proposed canon (awaiting product approval — no UI code until approved)  
**Layer:** L2 frontend / product UX canon  
**Date:** 2026-07-21  
**Language:** EN (technical canon). User-facing UI labels and examples in this doc: **RU**.  
**Parents:** [HOSTFLOW UX North Star](HOSTFLOW_UX_NORTH_STAR.md) · [ADR-011 UI Platform Standard](../architecture/ADR-011-hostflow-ui-platform-standard.md) · [C1 Inbox Workspace](../tasks/c1-communication-inbox-workspace.md) · [Sequential queue](../tasks/sales-to-comms-sequential-queue.md) · [Communication Platform Foundation](../architecture/communication-platform-foundation.md)  
**Implementation slice:** [conversation-workspace-v2 task](../tasks/conversation-workspace-v2.md)  
**Research context (L3, not SoT):** [communications-workspace-research.md](../workflows/communications-workspace-research.md)

---

## 1. Verdict

C1 delivered a working **Thread Workspace** on frozen platform contracts.  
The shipped UI still exposes the **Communication Engine** (channels, intents, delivery knobs, identifiers) instead of a **manager workplace**.

**Conversation Workspace v2** redesigns the UX only. It does **not** reopen Thread, ThreadContext, Commands, queues, or C2.

```text
C1 closed  = backend + workspace contracts complete
CW v2      = UX complete (frontend overlay)
C2         = Intent capability epic (independent)
```

---

## 2. Locked decisions

| Decision | Rule |
|----------|------|
| **C1 closed ≠ UX complete** | C1 acceptance covers contracts, Commands smoke, and a functional surface. Human-grade Conversation UX is **CW v2**. |
| **Pure frontend overlay** | CW v2 consumes frozen `ThreadContext` + Workspace Commands. No new mutation path. |
| **No backend / API / model changes** | Out of scope for this slice. Title stubs that originate in subject strings are **masked in UI** via human title resolution; fixing producers is a separate later concern. |
| **C2 continues independently** | Templates / Automations / Campaigns stay on their queue. CW v2 must not block or rewrite C2. |
| **One canon, two layout modes** | Inbox Center (`/app/inbox`, `/app/inbox/threads/:threadId`) and standalone (`/app/communications/threads/:threadId`) share the same UX law. |
| **«Новое письмо» is a separate flow** | Reply workspace must not become a universal composer. Compose-new is out of the reply surface. |
| **Default = manager actions only** | Platform controls live in advanced/debug surfaces and are **not** on the primary path. |

---

## 3. Product framing

The screen answers exactly three questions:

| Question | RU focus | Content |
|----------|----------|---------|
| **Кто?** | Who am I talking to? | Contact name, company, channel as thread fact, linked objects |
| **О чём?** | What is the conversation? | Full chronology (messages, attachments, notes, automation, SLA) |
| **Что сделать дальше?** | What should I do? | Primary: **Ответить** / **Позвонить** / create entity / **Закрыть разговор** |

North Star mapping ([HOSTFLOW UX North Star](HOSTFLOW_UX_NORTH_STAR.md)):

1. What is happening → timeline + human title  
2. Critical problem → SLA / delivery summary as signals, not forms  
3. What to do next → single Next Action + reply CTA  

**Anti-framing:** This is not an SMTP client, not a Platform admin console, and not a dump of ThreadContext fields.

---

## 4. Surfaces and layout modes

### 4.1 Shared law

Both surfaces must show the same:

- Human title (never UUID / inquiry stub in UI)
- Timeline-first work area
- Reply-first composer
- Unified linked objects
- Single Next Action surface
- Simplified default queues (Inbox Center list mode)

### 4.2 Layout modes

| Mode | Route family | Layout |
|------|--------------|--------|
| **Inbox Center** | `/app/inbox`, `/app/inbox/threads/:threadId` | 3 columns: queue list · conversation · linked objects |
| **Standalone thread** | `/app/communications/threads/:threadId` | 2 columns: conversation · linked objects (no queue list; optional back to inbox) |

Composition sketch (Inbox Center):

```text
┌──────────────┬────────────────────────────────┬────────────────────┐
│ Очередь      │ Кто? (human title + meta)      │ Связанные объекты  │
│              │                                │ (один блок)        │
│ Новые        │ О чём?                         │ · Кандидат         │
│ Ждут ответа  │ [timeline — primary focus]     │ · Компания         │
│ Мои          │                                │ · Заказ            │
│ Закрытые     │ Что дальше?                    │ · Следующее действие│
│ Все фильтры… │ [ Ответить ] → text → Отправить│                    │
└──────────────┴────────────────────────────────┴────────────────────┘
```

Standalone drops the left queue column; right rail and conversation law stay identical.

---

## 5. Human title

### 5.1 Display priority (UI)

Resolve for list row + work-area header (same function):

1. Company name (when linked)  
2. Contact / participant display name  
3. Email or phone  
4. Readable fallback (e.g. channel + short non-id phrase)  

**Never show in default UI:**

- Full thread UUID  
- Truncated UUID / inquiry id stubs (`3be27edd`)  
- Engine subjects like `Sales questionnaire · 3be27edd` as the primary title  

### 5.2 Acceptable header patterns (examples)

Primary:

```text
Pick a Job — анкета по сотрудничеству
Marek Puławski
biuro@pickajob.pl
```

Or stacked:

```text
Marek Puławski
Компания: Pick a Job
Тема: Анкета по сотрудничеству
```

Raw `subject` may feed a secondary «Тема» line **only after** scrubbing internal id suffixes. It must not be the sole title when company/contact exist.

### 5.3 Backend note (non-blocking)

Producers that embed ids into `subject` (e.g. Sales questionnaire pipeline) are **known debt**. CW v2 must not wait on backend fixes; UI masking is mandatory now.

---

## 6. Timeline-first work area

Timeline is the **main** product surface.

Expected chronology (grouped by day, e.g. **Сегодня**):

- входящее письмо  
- мой ответ  
- ответ клиента  
- вложение  
- автоматизация  
- заметка  
- SLA / work-state signals  

Rules:

- Timeline must remain visible and dominant while composing (composer is a bottom strip / expandable footer, not a form that replaces history).  
- Platform/debug strips (provider ids, raw delivery payloads) stay out of the default timeline.  
- Delivery problems surface as a compact signal + human explanation (C0.3 summary), not as an engineer console.

---

## 7. Reply-first composer

### 7.1 Default path (only)

```text
Ответить  →  пишет текст  →  Отправить
```

Default visible controls:

- Body (textarea)  
- **Отправить**  
- Optional: **Вставить шаблон** (appears after editor focus / reply open — not a prerequisite)  
- Optional secondary: internal note mode **only** if policy allows and presented as manager language («Внутренняя заметка»), not as a platform form section competing with reply  

### 7.2 Reply vs «Новое письмо»

| Concern | Reply workspace | Новое письмо (separate flow) |
|---------|-----------------|------------------------------|
| Subject | **Hidden / non-editable** — stays on thread | Editable |
| Channel | Thread fact (label only) | Chosen in that flow |
| Intent | Backend / ThreadContext default | Chosen in that flow if needed |
| Goal | Continue conversation | Start a new conversation |

Reply workspace **must not** grow into a universal composer that re-hosts compose-new fields.

### 7.3 Channel and Intent

- Thread already has a channel (e.g. Email). Do **not** re-select channel on reply.  
- Intent (e.g. `manual_outbound`) is a **platform** concept. Manager never picks it on the default path.  
- UI submits using ThreadContext defaults / allowed single default; backend remains authority.

---

## 8. Engine → UI mapping (mandatory)

What ThreadContext / Commands expose vs what default UI shows.

### 8.1 Hidden from default UI

| Engine / control | Default UI | Where (if anywhere) |
|------------------|------------|---------------------|
| Channel selector | **Hidden** | Advanced only if multi-channel reply is truly allowed *and* product explicitly enables it later |
| Intent selector | **Hidden** | Advanced / debug |
| Editable subject on reply | **Hidden** | Compose-new flow only |
| Delivery mode | **Hidden** | Advanced / debug |
| Send immediately | **Hidden** | Advanced / debug (default send uses platform policy) |
| Signature toggle | **Hidden** | Settings (**Настройки → Коммуникации**) or advanced |
| Template selector before focus | **Hidden** | «Вставить шаблон» after reply/editor focus |
| Internal identifiers (UUID, inquiry stubs, template ids, entity raw ids as titles) | **Hidden** | Debug |
| Provider / debug diagnostics | **Hidden** | Debug / delivery detail drawer |

### 8.2 Visible as manager language

| Signal | Presentation |
|--------|--------------|
| Channel | Fact label («Email»), not a `<select>` |
| Needs reply / waiting | Queue + header state chips in RU |
| SLA | One chip / signal |
| Delivery problem | Compact warning with human text from `delivery_summary` |
| Next action | Single surface (see §10) |
| Linked entities | One «Связанные объекты» block |

### 8.3 Still consumed (invisibly)

ThreadContext blocks `identity` · `work_state` · `capabilities` · `workspace` remain the read model.  
Composer stays dumb: it **uses** allowed intents/channels without **displaying** the engine vocabulary.

---

## 9. Queues and filters (Inbox Center)

### 9.1 Default chips (max four + overflow)

| Default chip (RU) | Maps to existing projection intent |
|-------------------|------------------------------------|
| **Новые** | New inbound / fresh attention |
| **Ждут ответа** | Requires reply (inbound waiting on operator) |
| **Мои** | Assigned to me |
| **Закрытые** | Closed / archived |

Plus: **Все фильтры** → remaining C1 queues (Delivery errors, Unresolved, Unassigned, Waiting for reply, All, …).

### 9.2 Rules

- Admin/diagnostic filters are not first-class chrome.  
- Sort and bulk tools stay secondary; they must not dominate the list header.  
- Queue writes remain forbidden (projections only) — unchanged from C1.

---

## 10. Linked objects and Next Action

### 10.1 One right-rail block: «Связанные объекты»

Collapse today’s separate widgets into one object:

- Кандидат  
- Компания  
- Заказ  
- Следующее действие  

Empty slots stay quiet (no four empty cards).

### 10.2 Single Next Action surface

**One** Next Action UI — not duplicated in header and rail.

Preferred: inside «Связанные объекты» as the action row, **or** a single sticky action bar above the composer — pick one in implementation and delete the other.

Commands remain: Set / Complete / Cancel Next Action (C1.2). UX change only.

---

## 11. Manager actions vs Platform controls

### 11.1 Default workspace — manager actions

Primary / secondary actions a manager may see:

- **Ответить**  
- **Позвонить** (when capability exists)  
- **Создать кандидата** / **Создать клиента** (when adapters allow)  
- **Закрыть разговор**  
- Assign / mark read (as lightweight commands, not a settings form)  
- Open linked entity  

### 11.2 Platform / advanced / debug

Never on the primary path:

- Intent vocabulary  
- Channel re-selection for single-channel threads  
- Delivery mode / send-immediately / signature toggles  
- Template registry browsing as a required step  
- Provider diagnostics, outbox ids, pipeline labels  
- Internal pipeline / capability dumps  

Access pattern: explicit **«Дополнительно»** / debug entry — collapsed, not competing with **Ответить**.

**Law:** Default workspace shows only manager actions. Platform controls are advanced/debug only and do not participate in the main user path.

---

## 12. Implementation phases (ordered)

No UI code before canon approval. After approval, implement in this order only:

| Phase | Focus | Exit criteria (short) |
|-------|-------|------------------------|
| **1** | Human title + timeline-first layout | UUID/stubs gone from list+header; timeline dominates work area on both layout modes |
| **2** | Reply-first composer | Default path = text + send; mapping §8.1 hidden; compose-new not hosted here |
| **3** | Simplified queues and filters | Four default chips + «Все фильтры» |
| **4** | Unified linked objects + single Next Action | One rail block; Next Action not duplicated |
| **5** | Visual cleanup and responsive modes | Density, mobile/narrow: timeline + reply survive; advanced stays tucked away |

---

## 13. Scope

### In

- Frontend overlay for Inbox Center + standalone thread  
- Title resolution, layout hierarchy, composer IA, filter IA, right rail IA  
- RU manager-facing copy for primary controls  

### Out

- Backend / API / Thread / ThreadContext / Command model changes  
- C2 Template / Automation / Campaign product work  
- Universal composer / «Новое письмо» inside reply workspace  
- New local reference dictionaries  
- Module business logic inside Communication UI  

---

## 14. Relationship to Epic C

| Track | Owns |
|-------|------|
| **C1** | Frozen contracts — complete |
| **CW v2** | Manager UX overlay — this canon |
| **C2** | `CommunicationIntent` emitters — independent |
| **Epic C Complete Gate** | Capability completeness after C2; CW v2 UX may land in parallel as FE work without reopening C1 contracts |

CW v2 is **not** a C2 slice and **must not** be filed under `epic-c2-*`.

---

## 15. Approval gate

Before any CW v2 UI PR:

- [ ] This canon approved (product + frontend owner)  
- [ ] Task slice phases unchanged unless this document is amended first  
- [ ] Explicit statement in PR: no backend/API/model changes  
- [ ] Diff limited to `hostflow-frontend` (+ docs if needed)  

---

## 16. Cross-references

- Task: [conversation-workspace-v2.md](../tasks/conversation-workspace-v2.md)  
- C1: [c1-communication-inbox-workspace.md](../tasks/c1-communication-inbox-workspace.md)  
- Queue: [sales-to-comms-sequential-queue.md](../tasks/sales-to-comms-sequential-queue.md)  
- C2 (out of scope for Inbox UX): [epic-c2-communication-campaigns.md](../tasks/epic-c2-communication-campaigns.md)  
- UI platform: [ADR-011](../architecture/ADR-011-hostflow-ui-platform-standard.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md)  
- North Star: [HOSTFLOW_UX_NORTH_STAR.md](HOSTFLOW_UX_NORTH_STAR.md)  

---

## History

- **2026-07-21:** Proposed — Conversation Workspace v2 as pure FE overlay; C1 closed ≠ UX complete; reply ≠ compose-new; mapping of hidden engine controls; five implementation phases.
