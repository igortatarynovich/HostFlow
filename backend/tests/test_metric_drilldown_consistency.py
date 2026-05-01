"""Structural test for the operational-metrics registry (G-3).

Spec: `docs/specs/operational-metrics.md`.

What this test enforces — fast, no DB, no network:

1. Every metric drilldown URL starts with one of the canonical
   frontend paths from `hostflow-frontend/src/app/crmAppPaths.generated.ts`.
   If a drilldown points to a path that doesn't exist in the route table,
   we'd ship a "View list" button leading to 404.
2. The query string is well-formed, lower-cased on the parameter name,
   and contains no whitespace. This catches typos like `?Stage=open`
   (case-sensitive in the frontend filter parsers) or copy-pasted
   labels with spaces.
3. Scope and silenced-filter values come from a closed enum so we don't
   accidentally invent a third meaning for "scope" in a future PR.
4. Metrics that share a backend source endpoint must agree on scope
   (we'd otherwise mix user-scoped and tenant-wide totals on the
   same widget — the historical Bug №2).

Counts/parity assertions against a real DB are intentionally out of scope
here; see "Out of scope" section of the spec for the follow-up plan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, List
from urllib.parse import parse_qsl, urlsplit

import pytest

from backend.app.constants.spa_paths import TASKS


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATED_PATHS_FILE = (
    REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "app"
    / "crmAppPaths.generated.ts"
)

ALLOWED_SCOPES: FrozenSet[str] = frozenset({"user", "team", "tenant"})
ALLOWED_SILENCED: FrozenSet[str] = frozenset({"default", "terminal_only"})
ALLOWED_PARITY: FrozenSet[str] = frozenset({"strict", "informational"})


@dataclass(frozen=True)
class Metric:
    id: str
    label_key: str
    source_endpoint: str
    source_field: str
    scope: str
    drilldown: str
    silenced_filter: str
    parity: str


# Mirror of `docs/specs/operational-metrics.md` §3.
# When you add a row to the spec table, add it here too — that's the contract.
REGISTRY: List[Metric] = [
    # 3.1 ops-counters
    Metric(
        id="ops.no_next_action_candidates",
        label_key="app.dashboard.ops.no_next_action_candidates",
        source_endpoint="GET /analytics/ops-counters",
        source_field="no_next_action_candidates",
        scope="user",
        drilldown="/app/candidates?next_action=missing&assignee=me",
        silenced_filter="default",
        parity="strict",
    ),
    Metric(
        id="ops.leads_no_next_action",
        label_key="app.dashboard.ops.leads_no_next_action",
        source_endpoint="GET /analytics/ops-counters",
        source_field="leads_no_next_action",
        scope="tenant",
        drilldown="/app/leads?next_action=missing",
        silenced_filter="default",
        parity="strict",
    ),
    Metric(
        id="ops.leads_sla_no_next_action_reminders",
        label_key="app.dashboard.ops.leads_sla_no_next_action",
        source_endpoint="GET /analytics/ops-counters",
        source_field="leads_sla_no_next_action_reminders",
        scope="user",
        drilldown=f"{TASKS}?type=leads_no_next_action&assignee_scope=mine",
        silenced_filter="default",
        parity="strict",
    ),
    Metric(
        id="ops.leads_sla_stuck_stage_reminders",
        label_key="app.dashboard.ops.leads_stuck_stage",
        source_endpoint="GET /analytics/ops-counters",
        source_field="leads_sla_stuck_stage_reminders",
        scope="user",
        drilldown=f"{TASKS}?type=leads_stuck_stage&assignee_scope=mine",
        silenced_filter="default",
        parity="strict",
    ),
    Metric(
        id="ops.unlinked_tasks",
        label_key="app.dashboard.ops.unlinked_tasks",
        source_endpoint="GET /analytics/ops-counters",
        source_field="unlinked_tasks",
        scope="user",
        drilldown=f"{TASKS}?t_layout=by_candidate&t_unlinked=1",
        silenced_filter="default",
        parity="strict",
    ),
    # 3.2 handoff
    Metric(
        id="handoff.requested",
        label_key="app.dashboard.handoff.requested",
        source_endpoint="GET /analytics/handoff-stats",
        source_field="total_requested",
        scope="tenant",
        drilldown="/app/candidates?handoff_status=any",
        silenced_filter="default",
        parity="informational",
    ),
    Metric(
        id="handoff.accepted",
        label_key="app.dashboard.handoff.accepted",
        source_endpoint="GET /analytics/handoff-stats",
        source_field="total_accepted",
        scope="tenant",
        drilldown="/app/candidates?handoff_status=accepted",
        silenced_filter="default",
        parity="strict",
    ),
    Metric(
        id="handoff.rejected",
        label_key="app.dashboard.handoff.rejected",
        source_endpoint="GET /analytics/handoff-stats",
        source_field="total_rejected",
        scope="tenant",
        drilldown="/app/candidates?handoff_status=rejected",
        silenced_filter="terminal_only",
        parity="strict",
    ),
    Metric(
        id="handoff.returned",
        label_key="app.dashboard.handoff.returned",
        source_endpoint="GET /analytics/handoff-stats",
        source_field="total_returned",
        scope="tenant",
        drilldown="/app/candidates?handoff_status=returned",
        silenced_filter="default",
        parity="strict",
    ),
    Metric(
        id="handoff.pending",
        label_key="app.dashboard.handoff.pending",
        source_endpoint="GET /analytics/handoff-stats",
        # Derived field — not a single column in the response. The dashboard
        # computes it as `requested - accepted - rejected - returned`. Documented
        # here so the metric has a single owner and the drilldown is stable.
        source_field="derived:total_requested_minus_terminal",
        scope="tenant",
        drilldown="/app/candidates?handoff_status=pending",
        silenced_filter="default",
        parity="strict",
    ),
    # 3.3 documents
    Metric(
        id="documents.missing",
        label_key="app.dashboard.documents.missing",
        source_endpoint="GET /analytics/document-stats",
        source_field="missing",
        scope="tenant",
        drilldown="/app/documents?quick=missing",
        silenced_filter="default",
        parity="informational",
    ),
    Metric(
        id="documents.in_progress",
        label_key="app.dashboard.documents.in_progress",
        source_endpoint="GET /analytics/document-stats",
        source_field="in_progress",
        scope="tenant",
        drilldown="/app/documents?quick=in_progress",
        silenced_filter="default",
        parity="informational",
    ),
    Metric(
        id="documents.ready",
        label_key="app.dashboard.documents.ready",
        source_endpoint="GET /analytics/document-stats",
        source_field="ready",
        scope="tenant",
        drilldown="/app/documents?quick=ready",
        silenced_filter="default",
        parity="informational",
    ),
    Metric(
        id="documents.rejected",
        label_key="app.dashboard.documents.rejected",
        source_endpoint="GET /analytics/document-stats",
        source_field="rejected",
        scope="tenant",
        drilldown="/app/documents?status=rejected",
        silenced_filter="default",
        parity="informational",
    ),
    # 3.4 funnel & stages — representative entries (one per template)
    Metric(
        id="funnel.stage_count.new",
        label_key="app.dashboard.funnel.stage_count.new",
        source_endpoint="GET /analytics/funnel",
        source_field="stages[].count",
        scope="tenant",
        drilldown="/app/candidates?stage=new",
        silenced_filter="default",
        parity="strict",
    ),
    Metric(
        id="funnel.rejected_by_reason.example",
        label_key="app.dashboard.funnel.rejected_by_reason.no_response",
        source_endpoint="GET /analytics/funnel",
        source_field="rejected_by_reason[]",
        scope="tenant",
        drilldown="/app/candidates?stage=rejected&status_reason=no_response",
        silenced_filter="terminal_only",
        parity="informational",
    ),
    Metric(
        id="funnel.declined_by_reason.example",
        label_key="app.dashboard.funnel.declined_by_reason.bad_offer",
        source_endpoint="GET /analytics/funnel",
        source_field="declined_by_reason[]",
        scope="tenant",
        drilldown="/app/candidates?stage=declined&status_reason=bad_offer",
        silenced_filter="terminal_only",
        parity="informational",
    ),
    # 3.5 risk intelligence
    Metric(
        id="risk.critical",
        label_key="app.dashboard.risk.critical",
        source_endpoint="GET /analytics/risk-intelligence",
        source_field="critical[]",
        scope="tenant",
        drilldown="/app/candidates?risk_level=critical",
        silenced_filter="default",
        parity="informational",
    ),
    Metric(
        id="risk.high",
        label_key="app.dashboard.risk.high",
        source_endpoint="GET /analytics/risk-intelligence",
        source_field="high[]",
        scope="tenant",
        drilldown="/app/candidates?risk_level=high",
        silenced_filter="default",
        parity="informational",
    ),
    # 3.6 communications SLA
    Metric(
        id="comms.sla_overdue_user",
        label_key="app.dashboard.comms.sla_overdue_user",
        source_endpoint="GET /communications/sla/incidents",
        source_field="total",
        scope="user",
        drilldown="/app/communications/sla?assignee_scope=mine",
        silenced_filter="default",
        parity="strict",
    ),
    Metric(
        id="comms.sla_overdue_team",
        label_key="app.dashboard.comms.sla_overdue_team",
        source_endpoint="GET /communications/sla/incidents",
        source_field="total",
        scope="tenant",
        drilldown="/app/communications/sla",
        silenced_filter="default",
        parity="strict",
    ),
]


def _generated_paths() -> List[str]:
    """Extract every right-hand-side string literal from `crmAppPaths.generated.ts`.

    The file is mechanically generated and follows `key: "/app/..."` syntax;
    we don't need a TS parser, just a regex over the literals.
    """
    text = GENERATED_PATHS_FILE.read_text(encoding="utf-8")
    return re.findall(r'"\s*(/app[^"]*)"', text)


def test_generated_paths_file_present() -> None:
    """Sanity: the generated path table must exist for the rest of the test to mean anything."""
    assert GENERATED_PATHS_FILE.is_file(), (
        f"missing {GENERATED_PATHS_FILE}. Run `npm run codegen:crm-app-paths`."
    )
    paths = _generated_paths()
    assert paths, "No paths extracted from generated file — regex or file format changed."


def test_registry_ids_unique() -> None:
    ids = [m.id for m in REGISTRY]
    assert len(ids) == len(set(ids)), f"duplicate metric ids: {sorted(ids)}"


@pytest.mark.parametrize("metric", REGISTRY, ids=lambda m: m.id)
def test_metric_enum_fields(metric: Metric) -> None:
    """Each metric uses values from the closed enums — no typos sneaking in."""
    assert metric.scope in ALLOWED_SCOPES, metric
    assert metric.silenced_filter in ALLOWED_SILENCED, metric
    assert metric.parity in ALLOWED_PARITY, metric
    assert metric.label_key.startswith("app."), (
        f"{metric.id}: label_key should be an i18n key under `app.` namespace"
    )


@pytest.mark.parametrize("metric", REGISTRY, ids=lambda m: m.id)
def test_metric_drilldown_well_formed(metric: Metric) -> None:
    """Drilldown URL parses, has no whitespace, and uses lower-case parameter names."""
    parts = urlsplit(metric.drilldown)
    assert parts.scheme == "" and parts.netloc == "", (
        f"{metric.id}: drilldown must be relative (no scheme/host): {metric.drilldown}"
    )
    assert parts.path.startswith("/app/"), (
        f"{metric.id}: drilldown path must start with /app/: {metric.drilldown}"
    )
    assert " " not in metric.drilldown, (
        f"{metric.id}: drilldown contains a space: {metric.drilldown}"
    )
    qs = parse_qsl(parts.query, keep_blank_values=False, strict_parsing=True)
    for key, value in qs:
        assert key == key.lower(), (
            f"{metric.id}: query param `{key}` must be lower-case"
        )
        assert value, f"{metric.id}: query param `{key}` has empty value"


@pytest.mark.parametrize("metric", REGISTRY, ids=lambda m: m.id)
def test_metric_drilldown_path_in_route_table(metric: Metric) -> None:
    """The path component of the drilldown must match a known frontend route prefix.

    We compare against the literal strings in `crmAppPaths.generated.ts` so any
    metric pointing to a deleted/renamed route fails CI before it ships.
    """
    drill_path = urlsplit(metric.drilldown).path
    known = set(_generated_paths())
    if drill_path in known:
        return
    # Allow nested resource URLs that live under a known prefix
    # (e.g. `/app/candidates/<id>` would match `/app/candidates`).
    assert any(
        drill_path == base or drill_path.startswith(base.rstrip("/") + "/")
        for base in known
    ), (
        f"{metric.id}: drilldown path `{drill_path}` not found in "
        f"crmAppPaths.generated.ts. If the route was renamed, regenerate "
        f"the path table and update the registry."
    )


def test_metric_source_scope_drilldown_uniqueness() -> None:
    """Two invariants that together kill the historical Bug №2:

    a) `(source_endpoint, source_field, scope)` is unique across the registry.
       The same endpoint counted in the same scope must come from a single metric;
       otherwise we'd ship two widgets that look different but compute the same
       number, and one of them will silently rot.

    b) When the same `(source_endpoint, source_field)` appears in multiple
       scopes (e.g. user-scoped *and* tenant-wide for the same SLA endpoint),
       each scope MUST link to a distinct drilldown URL — otherwise the user
       scope card opens the tenant list and the parity claim is violated.

    Note: same endpoint with *different* fields is fine (e.g. handoff.pending
    vs handoff.accepted both come from `/handoff-stats`).
    """
    by_full_key: dict[tuple[str, str, str], list[Metric]] = {}
    by_field: dict[tuple[str, str], list[Metric]] = {}
    for m in REGISTRY:
        by_full_key.setdefault(
            (m.source_endpoint, m.source_field, m.scope), []
        ).append(m)
        by_field.setdefault((m.source_endpoint, m.source_field), []).append(m)

    for key, entries in by_full_key.items():
        assert len(entries) == 1, (
            f"(endpoint, field, scope)={key} appears {len(entries)} times "
            f"in registry: {[m.id for m in entries]}"
        )

    for (endpoint, field), entries in by_field.items():
        if len(entries) == 1:
            continue
        drills = [m.drilldown for m in entries]
        assert len(set(drills)) == len(drills), (
            f"endpoint={endpoint} field={field} reused across scopes "
            f"{[m.scope for m in entries]} but drilldown URLs collide: {drills}"
        )
