# Stage 1B — Quote Lifecycle Sequences

**Status:** design-first (revision 3)

---

## 1. Send v2 after revise (valid_until + supersede)

```mermaid
sequenceDiagram
    participant SVC as QuoteService
    participant DB as PostgreSQL

    Note over SVC,DB: v1 already sent with valid_until=T1

    SVC->>DB: send v2
    SVC->>DB: v2.valid_until=T2 frozen, v2.sent_at=now
    SVC->>DB: v1.version_status=superseded (valid_until T1 unchanged)
    SVC->>DB: quote.last_sent_at, current_valid_until=T2
```

---

## 2. Accept — latest sent only

```mermaid
sequenceDiagram
    actor M as Manager
    participant API as Quotes API

    M->>API: POST /accept {version_id: v1_id}
    Note over API: v2 is latest sent
    API-->>M: 409 stale_version

    M->>API: POST /accept {version_id: v2_id}
    API-->>M: 200 accepted_version_id=v2
```

---

## 3. Expire

Checks `latest_sent_version.valid_until`, sets `last_expired_at`.

---

## 4. Reject → revise (same quote_id)

Negotiation continues without new Quote aggregate.
