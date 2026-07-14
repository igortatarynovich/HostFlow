# Backend Transaction Boundary Rule

**Status:** canonical (L3 implementation rule)  
**Scope:** all backend domain modules  
**Related:** Stage 1A `convert-client`, ADR-020

## Rule

**Nested domain/service functions must not call `commit()`.**  
The transaction owner is the **application service** or **router/use-case boundary** that orchestrates the workflow.

## Rationale

Internal `commit()` in lower layers:

- expires ORM objects in the caller session (`MissingGreenlet` in async SQLAlchemy);
- breaks atomic multi-entity workflows (e.g. Lead → ClientAccount → Company);
- hides partial persistence on failure (orphan rows).

Stage 1A example: `create_company_service(..., commit=False)` when invoked from `convert_client_lead()`; single `commit()` at the router after the use-case completes.

## Allowed patterns

| Layer | May `commit()`? | Notes |
|-------|-----------------|-------|
| Router / CLI / job entrypoint | Yes | One commit per successful use-case |
| Application service (use-case) | Sometimes | Only when it is the orchestration root |
| Domain service / CRUD helper | **No** | `flush()` only; return IDs or detached DTOs |
| Background worker step | Yes | Own session per message/job |

## Required API for shared services

When a service is reused both standalone (HTTP create) and inside a larger transaction:

```python
async def create_company_service(..., *, commit: bool = True) -> Company:
    company = await crud.create_company(...)
    if not commit:
        return company
    await session.commit()
    ...
```

Default `commit=True` preserves existing HTTP behaviour; orchestrators pass `commit=False`.

## Enforcement

- Code review: flag `session.commit()` / `await db.commit()` below router/application-service layer.
- Regression tests: multi-entity flows must assert rollback on mid-flow failure (see Stage 1A conversion tests).
- Future modules (Quote, CommercialConfirmation, ServiceOrder) must follow the same boundary.
