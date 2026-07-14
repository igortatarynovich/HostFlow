# Stage 1B — Quote Lifecycle Sequences

**Status:** design-first (revision 2)  
**Parent:** [`stage-1b-quote-foundation-implementation-contract.md`](../tasks/stage-1b-quote-foundation-implementation-contract.md)

---

## 1. Create draft quote

```mermaid
sequenceDiagram
    actor M as Manager
    participant API as Quotes API
    participant SVC as QuoteService
    participant DB as PostgreSQL

    M->>API: POST /api/v1/quotes
    API->>SVC: create_quote()
    SVC->>DB: INSERT quote (status=draft, lock_version=1)
    SVC->>DB: INSERT quote_version (v1, version_status=draft)
    SVC->>DB: UPDATE quote.current_version_id (deferred FK)
    SVC-->>API: QuoteOut
    API-->>M: 201
```

---

## 2. Send quote (freeze version)

```mermaid
sequenceDiagram
    actor M as Manager
    participant API as Quotes API
    participant SVC as QuoteService
    participant DB as PostgreSQL

    M->>API: POST /quotes/{id}/send  If-Match: lock_version
    API->>SVC: send_quote()
    SVC->>DB: SELECT quote FOR UPDATE
    SVC->>SVC: assert own_company_id, currency, money rules
    SVC->>DB: UPDATE version SET version_status=sent, sent_at=now(), snapshot frozen
    SVC->>DB: UPDATE quote SET status=sent, lock_version++
    API-->>M: 200 QuoteOut
```

---

## 3. Counter-offer (revise)

```mermaid
sequenceDiagram
    actor M as Manager
    participant API as Quotes API
    participant SVC as QuoteService
    participant DB as PostgreSQL

    Note over M,DB: Quote status sent | rejected | expired

    M->>API: POST /quotes/{id}/revise  If-Match: lock_version
    API->>SVC: revise_quote()
    SVC->>DB: SELECT quote FOR UPDATE
    SVC->>DB: INSERT quote_version (vN+1, version_status=draft)
    SVC->>DB: UPDATE quote SET status=revision_draft, current_version_id=vN+1
    API-->>M: 200 QuoteOut (v1..vN sent rows unchanged)
```

---

## 4. Accept specific sent version

```mermaid
sequenceDiagram
    actor M as Manager
    participant API as Quotes API
    participant SVC as QuoteService
    participant DB as PostgreSQL

    M->>API: POST /quotes/{id}/accept {version_id, acceptance_source}
    API->>SVC: accept_quote()
    SVC->>DB: SELECT quote FOR UPDATE
    alt version not sent or wrong quote
        API-->>M: 409 stale_version
    else
        SVC->>DB: UPDATE quote SET status=accepted, accepted_version_id, accepted_by_user_id
        API-->>M: 200 (Sale terminal — no Service Order)
    end
```

---

## 5. Reject → revise (same thread)

```mermaid
sequenceDiagram
    actor M as Manager
    participant API as Quotes API

    M->>API: POST /quotes/{id}/reject
    API-->>M: 200 status=rejected
    M->>API: POST /quotes/{id}/revise
    API-->>M: 200 status=revision_draft, new draft version
    Note over M,API: Same quote_id — negotiation continues
```

---

## 6. Quote → Service Order (next PR)

```mermaid
sequenceDiagram
    participant API as Orders API
    participant DB as PostgreSQL

    Note over API,DB: Preconditions: status=accepted, accepted_version_id set

    API->>DB: COPY accepted_version.scope_snapshot → service_order
    Note over API,DB: Quote row unchanged
```

---

## 7. Vertical isolation

Quote sequences do not touch intake/provisioning (`provision_targeted_advertising_*`, questionnaire invite).
