"""C1.2 close-out — optimistic concurrency + Command coverage + no mixed path."""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.communications.workspace_commands import (
    THREAD_FIELD_COMMAND_COVERAGE,
    WorkspaceCommandError,
    assign_thread,
    expect_work_version,
    mark_thread_read,
)
from backend.app.models.communication import CommunicationThread
from backend.app.models.own_company import OwnCompany

REPO = Path(__file__).resolve().parents[3]
ROUTES_DIR = REPO / "backend" / "app" / "api" / "v1" / "communications" / "routes"
FE_SRC = REPO / "hostflow-frontend" / "src"


async def _oc(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .limit(1)
    )
    oc = row.scalar_one_or_none()
    if oc is None:
        oc = str(uuid.uuid4())
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name="OC cov"))
        await db.flush()
    return str(oc)


@pytest.mark.asyncio
async def test_stale_work_version_conflicts(db, tenant_id: str, bootstrap: dict):
    oc = await _oc(db, tenant_id)
    me = str(bootstrap["recruiter_id"])
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        channel="email",
        status="open",
        subject="ver",
        unread_count=2,
        work_version=1,
    )
    db.add(thread)
    await db.flush()

    with expect_work_version(1):
        first = await mark_thread_read(
            db, tenant_id=tenant_id, thread=thread, actor_user_id=me
        )
    assert first.applied is True
    assert int(first.context.work_state["work_version"]) == 2

    with pytest.raises(WorkspaceCommandError) as ei:
        with expect_work_version(1):
            await assign_thread(
                db,
                tenant_id=tenant_id,
                thread=thread,
                actor_user_id=me,
                assignee_id=me,
                reason="manual",
            )
    assert ei.value.code == "stale_work_version"

    with expect_work_version(2):
        ok = await assign_thread(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=me,
            assignee_id=me,
            reason="manual",
        )
    assert ok.applied is True
    assert int(ok.context.work_state["work_version"]) == 3


def test_command_coverage_map_complete():
    required = {
        "assignee_id",
        "unread_count",
        "is_archived",
        "status",
        "priority",
        "tags_json",
        "thread_meta",
        "linked_candidate_id",
        "linked_company_id",
        "sla_due_at",
    }
    assert required <= set(THREAD_FIELD_COMMAND_COVERAGE.keys())
    for field, cmds in THREAD_FIELD_COMMAND_COVERAGE.items():
        if field == "work_version":
            continue
        assert cmds, f"{field} must map to at least one Command"


def test_no_legacy_patch_or_read_routes():
    threads_py = (ROUTES_DIR / "threads.py").read_text(encoding="utf-8")
    assert "async def patch_thread" not in threads_py
    assert '"/threads/{thread_id}/read"' not in threads_py
    assert "@router.patch" not in threads_py


def test_fe_workspace_has_no_live_patch_calls():
    offenders: list[str] = []
    for path in FE_SRC.rglob("*.{ts,tsx}".replace("{ts,tsx}", "*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "patchCommunicationThread(" in text and "throw new Error" not in text:
            # Allow the deprecated stub definition only.
            if path.name == "communications.ts" and "removed in C1.2" in text:
                continue
            offenders.append(str(path.relative_to(REPO)))
    assert offenders == [], f"FE still calls patchCommunicationThread: {offenders}"


def test_http_routes_do_not_assign_thread_workspace_fields():
    """No-mixed-path: Workspace-mutating field writes live in workspace_commands(+workflow)."""
    allowed_files = {
        "workspace_commands.py",  # HTTP adapters only — should not assign thread.*
    }
    forbidden_attrs = {
        "assignee_id",
        "unread_count",
        "is_archived",
        "priority",
        "tags_json",
        "thread_meta",
        "linked_candidate_id",
        "linked_company_id",
        "sla_due_at",
        "status",
        "queue_assigned_by",
    }
    # Maintenance / create paths still touch Thread outside Commands by design:
    # create_thread, reconcile-unread, assign-auto, ingest (other package).
    allowlist_route_files = {
        "threads.py",  # create + reconcile + assign-auto
        "ingest.py",
        "messages.py",  # last_message_* projections
        "workspace_commands.py",  # must not mutate directly
    }
    hits: list[str] = []
    for path in ROUTES_DIR.glob("*.py"):
        if path.name in allowlist_route_files and path.name != "workspace_commands.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "thread"
                    and target.attr in forbidden_attrs
                ):
                    hits.append(f"{path.name}:{node.lineno} thread.{target.attr}")
    assert hits == [], f"Route modules mutate Thread fields directly: {hits}"
