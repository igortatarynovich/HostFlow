# Stage 1B — Quote UI Wireflow (design only)

**Status:** design-first — **no frontend in PR-1**  
**Surface canon:** [`ui-constitution-v1.md`](../architecture/ui-constitution-v1.md)  
**Parent:** [`stage-1b-quote-foundation-implementation-contract.md`](../tasks/stage-1b-quote-foundation-implementation-contract.md)

---

## 1. Product vocabulary

| UI (RU) | Domain object | Forbidden |
|---------|---------------|-----------|
| **Коммерческое предложение** | Quote | «КП» as DB term in code |
| **Клиент** | ClientAccount | Company as primary client label |
| **Обращение** | Sales Inquiry (Lead transport) | «Лид» |

Quote lives under **Client workspace**, not Sales Inbox.

---

## 2. Entry points (future UI PR)

```text
/app/clients/:clientAccountId
    └── Tab: «Предложения» (Quotes list)
            └── /app/clients/:id/quotes/:quoteId (Entity detail)
```

Secondary entry (later):

```text
/app/sales/inquiries/:id
    └── Action: «Создать предложение» → prefills client_account_id + source_lead_id
```

---

## 3. Screen map

| Screen type | Route | Purpose |
|-------------|-------|---------|
| Collection | `…/quotes` | List by status |
| Entity Detail | `…/quotes/:id` | Draft edit + lifecycle actions |
| Modal | send confirm | Confirm freeze + valid_until |
| Toast | — | Transition feedback |

**No new primary nav item.** Quotes are a facet of Client entity per UI constitution.

---

## 4. Wireflow — happy path (targeting)

```text
[Sales Inquiry converted]
        ↓
[Client Account detail]
        ↓ user clicks «Новое предложение»
[Quote draft composer]
  - service_family: targeted_advertising (preset)
  - line items table
  - notes_client
  - valid_until picker (draft version — frozen on send)
        ↓ «Отправить клиенту»
[Send confirmation modal]
  - shows scope_snapshot summary
  - warns: terms will freeze
        ↓ confirm
[Quote detail — status: Отправлено]
        ↓ external client decision (out of band in PR-1)
[Manager marks: Принято / Отклонено]
[Quote detail — status: Odrzucono / Wygasło]
        ↓ «Nowa wersja oferty» (revise)
[Quote detail — revision_draft, v2]
        ↓ Send v2
[Quote detail — sent]
        ↓ Accept v2
[Quote detail — accepted, terminal]
```

---

## 5. Status chips

| status | RU label | Color token |
|--------|----------|-------------|
| draft | Черновик | neutral |
| revision_draft | Новая редакция | neutral |
| sent | Отправлено | info |
| accepted | Принято | success |
| rejected | Отклонено | danger |
| expired | Истекло | warning |

---

## 6. Actions by status

| status | Primary actions | Disabled |
|--------|-----------------|----------|
| draft | Save, Send | Accept, Revise |
| revision_draft | Save, Send | Accept |
| sent | Accept (latest only), Reject, Expire, Revise | Edit sent version; accept older round blocked |
| accepted | View only | All mutations |
| rejected | Revise, View history | Accept until new send |
| expired | Revise, View history | Accept until new send |

---

## 7. Empty states

| Context | Copy (RU) |
|---------|-----------|
| No quotes on client | «Коммерческих предложений пока нет. Создайте первое предложение для этого клиента.» |
| Draft incomplete | «Добавьте позиции и срок действия перед отправкой.» |

---

## 8. Explicit non-goals (UI)

- Service Order creation button (next PR)
- Invoice preview
- Commercial Confirmation checklist
- Client self-service portal
- Quote PDF export

---

## 9. API mapping (for future frontend)

| UI action | API |
|-----------|-----|
| Create | `POST /api/v1/quotes` |
| Autosave draft | `PATCH /api/v1/quotes/{id}` |
| Send | `POST /api/v1/quotes/{id}/send` |
| Counter-offer | `POST /api/v1/quotes/{id}/revise` |
| Accept | `POST /api/v1/quotes/{id}/accept` |
| Reject | `POST /api/v1/quotes/{id}/reject` |
| List | `GET /api/v1/quotes?client_account_id=` |
