"""Per-topic HTTP routers for the communications API.

Each submodule in this package owns a focused slice of endpoints and
exposes them via its own :class:`fastapi.APIRouter` named ``router``.
The parent :mod:`backend.app.api.v1.communications` package mounts each
sub-router into its own prefixed router via ``router.include_router(...)``,
so URL paths and the public OpenAPI schema are unchanged.

Phase 1 god-module split, step 3/N. Topics extracted so far:

* ``audit``    — allocator preview / audit + commands audit endpoints.
* ``planner``  — working-hours, time-off requests, notification settings.
                 Phase 2.1 (ADR-012, 2026-05-09): legacy planner-event
                 routes were removed; canonical task / planner CRUD is
                 ``/api/v1/activities``.
* ``oauth``    — channel-account OAuth start / complete / refresh +
                 sync-cursor get / patch.

Pending extractions (further sub-steps):
``threads``, ``messages``, ``dispatch``, ``accounts``, ``webhooks``,
``ingest``, ``settings``.
"""
