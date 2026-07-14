# Stage 1B — Quote Lifecycle Sequences

**Status:** design-first  
**Parent:** [`stage-1b-quote-foundation-implementation-contract.md`](../tasks/stage-1b-quote-foundation-implementation-contract.md)

---

## 1. Create draft quote

```mermaid
sequenceDiagram
    actor M as Manager
    participant API as Quotes API
    participant SVC as QuoteService
    participant CA as ClientAccount store
    participant DB as PostgreSQL

    M->>API: POST /api/v1/quotes
    API->>SVC: create_quote(payload)
    SVC->>CA: assert_client_account_in_tenant()
    CA-->>SVC: account row
    SVC->>DB: INSERT quotes (status=draft)
    SVC->>DB: INSERT quote_versions (v1, scope_snapshot draft)
    SVC->>DB: UPDATE quotes.current_version_id
    SVC-->>API: QuoteOut
    API-->>M: 201 Created
```

---

## 2. Send quote (freeze snapshot)

```mermaid
sequenceDiagram
    actor M as Manager
    participant API as Quotes API
    participant SVC as QuoteService
    participant DB as PostgreSQL

    M->>API: POST /api/v1/quotes/{id}/send
    API->>SVC: send_quote(id)
    SVC->>DB: SELECT quote FOR UPDATE
    alt status != draft
        SVC-->>API: 409 Conflict
    else status = draft
        SVC->>SVC: enrich scope_snapshot (client_account, captured_at)
        SVC->>DB: UPDATE quote_versions SET scope_snapshot=frozen
        SVC->>DB: UPDATE quotes SET status=sent, sent_at=now()
        SVC-->>API: QuoteOut
        API-->>M: 200 OK
    end
```

---

## 3. Accept quote (Sale layer only)

```mermaid
sequenceDiagram
    actor M as Manager
    participant API as Quotes API
    participant SVC as QuoteService
    participant DB as PostgreSQL

    Note over SVC: PR-1 stops here — no Service Order

    M->>API: POST /api/v1/quotes/{id}/accept
    API->>SVC: accept_quote(id, version_id?)
    SVC->>DB: SELECT quote FOR UPDATE
    alt status != sent
        SVC-->>API: 409 invalid_transition
    else version_id != current_version_id
        SVC-->>API: 409 stale_version
    else
        SVC->>DB: UPDATE quotes SET status=accepted, accepted_at=now(), accepted_version_id=current_version_id
        SVC-->>API: QuoteOut
        API-->>M: 200 OK
    end
```

---

## 4. Future: Quote → Service Order (next PR — not implemented)

```mermaid
sequenceDiagram
    actor M as Manager
    participant API as Orders API
    participant QS as QuoteService
    participant OS as ServiceOrderService
    participant DB as PostgreSQL

    Note over API,DB: Stage 1B+ follow-on PR only

    M->>API: POST /api/v1/service-orders/from-quote/{quoteId}
    API->>QS: load_accepted_quote()
    QS-->>API: quote + frozen scope_snapshot
    API->>OS: create_from_quote_snapshot()
    OS->>DB: INSERT service_orders (client_account_id, scope_snapshot copy)
    OS-->>API: ServiceOrderOut
    API-->>M: 201 Created
```

---

## 5. Boundary diagram (vertical isolation)

```mermaid
flowchart LR
    subgraph intake [Intake — merged]
        F[Targeted-advertising form]
        L[Sales Inquiry]
    end
    subgraph identity [Identity — merged]
        CA[ClientAccount]
    end
    subgraph sale [Sale — Stage 1B PR-1]
        Q[Quote + Versions]
    end
    subgraph order [Order — next PR]
        SO[ServiceOrder]
    end
    subgraph commerce [Commerce — later]
        CC[CommercialConfirmation]
        INV[Invoice]
    end

    F --> L
    L --> CA
    CA --> Q
    Q -.->|next PR| SO
    SO -.-> CC
    CC -.-> INV
```

---

## 6. Recovery / legacy paths (no Quote interaction)

Auto-seed and lazy ensure remain in **intake** vertical. Quote PR must not modify:

- `provision_targeted_advertising_*`
- `ensure_tenant_targeted_advertising_intake_form`
- Questionnaire invite resolution

Legacy services tenants without quote rows continue to work; first quote is explicit user action.
