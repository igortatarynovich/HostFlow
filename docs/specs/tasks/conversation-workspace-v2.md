# Conversation Workspace v2 — implementation slice

**Status:** Spec ready — **blocked on canon approval** (no UI code until approved)  
**Type:** Frontend UX overlay (not an Epic C2 slice)  
**Branch (proposed):** `feat/conversation-workspace-v2` (open only after approval; one phase per PR preferred)  
**Canon:** [Conversation Workspace v2](../frontend/conversation-workspace-v2.md)  
**Parents:** [C1 Inbox Workspace](c1-communication-inbox-workspace.md) · [Sequential queue](sales-to-comms-sequential-queue.md) · [HOSTFLOW UX North Star](../frontend/HOSTFLOW_UX_NORTH_STAR.md) · [ADR-011](../architecture/ADR-011-hostflow-ui-platform-standard.md)

---

## Locked constraints

1. **C1 closed = contracts complete, not UX complete.**  
2. **Pure frontend overlay** over frozen ThreadContext + Workspace Commands.  
3. **No backend / API / model changes** in this slice.  
4. **C2 continues independently** — do not park C2 for CW v2; do not put CW v2 under `epic-c2-*`.  
5. **Surfaces:** Inbox Center + standalone `/communications/threads/:id` — one canon, two layout modes.  
6. **«Новое письмо»** = separate flow; reply workspace must not become a universal composer.  
7. **Default UI = manager actions only.** Platform controls only in advanced/debug.

---

## Goal

Replace the Communication Engine control panel with a manager Conversation Workspace that answers:

1. **Кто?**  
2. **О чём?**  
3. **Что сделать дальше?**

Primary reply path:

```text
Ответить → текст → Отправить
```

---

## Phases (do not reorder)

### Phase 1 — Human title + timeline-first layout

- [ ] Shared `threadTitle()` / header resolution: company → contact → email/phone → readable fallback  
- [ ] Strip / never surface UUID and inquiry-id subject stubs as primary title  
- [ ] Timeline dominates work area on Inbox Center and standalone  
- [ ] Composer does not replace chronology  

**Exit:** No internal id in list title or header; timeline is the visual center.

### Phase 2 — Reply-first composer

- [ ] Default: body + **Отправить**  
- [ ] Hide from default UI (canon §8.1): channel selector, intent selector, editable subject on reply, delivery mode, send immediately, signature toggle, template selector before focus, internal identifiers, provider/debug diagnostics  
- [ ] «Вставить шаблон» only after reply/editor focus  
- [ ] Channel shown as fact label; intent taken from ThreadContext defaults  
- [ ] Do not host «Новое письмо» fields in reply workspace  

**Exit:** Manager can reply without seeing platform vocabulary.

### Phase 3 — Simplified queues and filters

- [ ] Default chips: **Новые** · **Ждут ответа** · **Мои** · **Закрытые**  
- [ ] Remaining C1 queues under **Все фильтры**  
- [ ] Inbox Center only (standalone unchanged)  

**Exit:** List chrome matches manager queues, not admin filter farm.

### Phase 4 — Unified linked objects + single Next Action

- [ ] One right-rail block «Связанные объекты» (кандидат / компания / заказ / следующее действие)  
- [ ] Remove duplicate Next Action surfaces (header vs rail — keep one)  
- [ ] Same Commands as C1.2  

**Exit:** One object block; one Next Action UI.

### Phase 5 — Visual cleanup and responsive modes

- [ ] Density / hierarchy pass per ADR-011 + North Star  
- [ ] Narrow/mobile: timeline + reply survive; advanced stays collapsed  
- [ ] Remove leftover engine chrome from default path  

**Exit:** Both layout modes feel like one product, not a debug console.

---

## Out of scope

- Alembic / API / ThreadContext shape / new Commands  
- C2 template/automation/campaign engines  
- Compose-new product flow (track separately)  
- Backend subject-string producer fixes (optional follow-up; UI masking is enough for CW v2)

---

## Validation (per phase PR)

- [ ] Diff limited to `hostflow-frontend` (+ this docs tree if amended)  
- [ ] Explicit PR note: no backend/API/model changes  
- [ ] Manual: open Inbox Center thread + standalone thread — title human, reply path short  
- [ ] `npm run build` (frontend) green  
- [ ] No new local dictionaries; no cross-module internal imports  

---

## Sequencing vs Epic C

| Track | Status vs this slice |
|-------|----------------------|
| C1 | Closed — contracts SoT |
| C2 | Active — **do not block** |
| CW v2 | Parallel FE after canon approval |
| Epic C Complete Gate | Unchanged; does not require CW v2 for C2 completion |

---

## History

- **2026-07-21:** Slice opened as docs-only; UI blocked on canon approval.
