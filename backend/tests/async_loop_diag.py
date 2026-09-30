"""CI-only trace for the Mapping Resolution Gate async failure.

Prints loop, thread, and connection identity. Does not alter fixture
control flow, assertions, or which runner executes a test. Active only when
``GITHUB_ACTIONS=true`` or ``HOSTFLOW_ASYNC_LOOP_DIAG=1`` and the session
collects ``test_mapping_resolve.py``.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import sys
import threading
import time
from typing import Any


_capmanager: Any = None


def set_capmanager(manager: Any) -> None:
    global _capmanager
    _capmanager = manager


def _emit(line: str) -> None:
    # Suspend pytest's fd capture so the line is in the Actions log
    # whether the test passes or fails.
    manager = _capmanager
    if manager is None:
        sys.__stderr__.write(line + "\n")
        sys.__stderr__.flush()
        return
    with manager.global_and_fixture_disabled():
        sys.__stderr__.write(line + "\n")
        sys.__stderr__.flush()


_PREFIX = "ASYNC-LOOP-DIAG"
_installed = False
_current_nodeid = ""
_t0 = time.monotonic()


def enabled() -> bool:
    if os.environ.get("HOSTFLOW_ASYNC_LOOP_DIAG", "").strip() in ("1", "true", "yes"):
        return True
    return os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"


def _mapping_node(nodeid: str) -> bool:
    return "test_mapping_resolve.py" in nodeid


def _loop_bits() -> str:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return "loop=none"
    policy = asyncio.get_event_loop_policy()
    task = asyncio.current_task()
    task_s = "none" if task is None else f"{id(task)}:{task.get_name()}"
    return (
        f"loop={id(loop)}:{type(loop).__module__}.{type(loop).__name__} "
        f"policy={type(policy).__module__}.{type(policy).__name__} "
        f"task={task_s}"
    )


def _thread_bits() -> str:
    thread = threading.current_thread()
    return f"pid={os.getpid()} tid={threading.get_ident()} thread={thread.name}"


def _raw_dbapi(dbapi: Any) -> Any:
    raw = getattr(dbapi, "driver_connection", None)
    if raw is None:
        raw = getattr(dbapi, "_connection", None)
    return raw if raw is not None else dbapi


def _conn_bits(dbapi: Any) -> str:
    raw = _raw_dbapi(dbapi)
    parts = [f"dbapi={id(dbapi)}", f"dbapi_type={type(dbapi).__name__}", f"raw={id(raw)}"]
    closed = getattr(raw, "is_closed", None)
    if callable(closed):
        try:
            parts.append(f"closed={int(bool(closed()))}")
        except Exception:
            parts.append("closed=?")
    conn_loop = getattr(raw, "_loop", None)
    if conn_loop is not None:
        try:
            running = asyncio.get_running_loop()
            match = int(conn_loop is running)
        except RuntimeError:
            match = 0
        parts.append(f"conn_loop={id(conn_loop)} loop_match={match}")
    exclusive = getattr(raw, "_stmt_exclusive_section", None)
    if exclusive is not None:
        parts.append(f"exclusive={getattr(exclusive, '_acquired', '?')}")
    return " ".join(parts)


def _session_bits(session: Any) -> str:
    if session is None:
        return "session=none"
    parts = [f"session={id(session)}"]
    sync = getattr(session, "sync_session", None)
    if sync is None:
        return " ".join(parts)
    parts.append(f"sync_session={id(sync)}")
    trans = None
    try:
        trans = sync.get_transaction()
    except Exception:
        trans = None
    conn = getattr(trans, "connection", None) if trans is not None else None
    if conn is None:
        parts.append("sa_conn=none")
        return " ".join(parts)
    parts.append(f"sa_conn={id(conn)}")
    dbapi = getattr(conn, "dbapi_connection", None)
    if dbapi is None:
        dbapi = getattr(conn, "connection", None)
    if dbapi is not None and not isinstance(dbapi, type):
        parts.append(_conn_bits(dbapi))
    return " ".join(parts)


def trace(phase: str, nodeid: str = "", *, session: Any = None, error: BaseException | None = None, force: bool = False) -> None:
    """One stdout line. Never raises."""
    if not _installed:
        return
    node = nodeid or _current_nodeid
    if not force and phase not in {"CHECKOUT", "CHECKIN"} and not _mapping_node(node):
        return
    try:
        elapsed = time.monotonic() - _t0
        fields = [
            _PREFIX,
            phase,
            f"t={elapsed:.3f}",
            _thread_bits(),
            _loop_bits(),
            f"node={node}",
        ]
        if session is not None or phase.endswith("SESSION") or phase in {"DB-YIELD", "TEST-ENTER", "TEST-EXIT"}:
            fields.append(_session_bits(session))
        if error is not None:
            fields.append(f"error={type(error).__name__}: {error}")
        _emit(" ".join(fields))
    except Exception:
        return


def _on_checkout(dbapi_connection: Any, connection_record: Any, connection_proxy: Any) -> None:
    try:
        if not _installed:
            return
        extra = f"rec={id(connection_record)} proxy={id(connection_proxy)} {_conn_bits(dbapi_connection)}"
        elapsed = time.monotonic() - _t0
        _emit(
            " ".join(
                [
                    _PREFIX,
                    "CHECKOUT",
                    f"t={elapsed:.3f}",
                    _thread_bits(),
                    _loop_bits(),
                    f"node={_current_nodeid}",
                    extra,
                ]
            )
        )
    except Exception:
        return


def _on_checkin(dbapi_connection: Any, connection_record: Any) -> None:
    try:
        if not _installed:
            return
        extra = f"rec={id(connection_record)} {_conn_bits(dbapi_connection)}"
        elapsed = time.monotonic() - _t0
        _emit(
            " ".join(
                [
                    _PREFIX,
                    "CHECKIN",
                    f"t={elapsed:.3f}",
                    _thread_bits(),
                    _loop_bits(),
                    f"node={_current_nodeid}",
                    extra,
                ]
            )
        )
    except Exception:
        return


def _wrap_test(item: Any) -> None:
    orig = item.obj
    if not inspect.iscoroutinefunction(orig):
        return

    async def _wrapped(*args: Any, **kwargs: Any) -> Any:
        session = kwargs.get("db")
        if session is None:
            for value in args:
                if hasattr(value, "sync_session"):
                    session = value
                    break
        trace("TEST-ENTER", item.nodeid, session=session, force=True)
        try:
            return await orig(*args, **kwargs)
        finally:
            trace("TEST-EXIT", item.nodeid, session=session, force=True)

    _wrapped.__signature__ = inspect.signature(orig)  # type: ignore[attr-defined]
    _wrapped.__wrapped__ = orig  # type: ignore[attr-defined]
    _wrapped.__name__ = orig.__name__
    _wrapped.__qualname__ = getattr(orig, "__qualname__", orig.__name__)
    item.obj = _wrapped


class _Plugin:
    def pytest_runtest_setup(self, item: Any) -> None:
        global _current_nodeid
        _current_nodeid = getattr(item, "nodeid", "")
        trace("RUNTEST-SETUP", _current_nodeid, force=True)


def maybe_install(config: Any, items: list[Any]) -> None:
    """Register pool listeners once per session that collects the mapping tests."""
    global _installed
    if _installed or not enabled():
        return
    if not any(_mapping_node(getattr(item, "nodeid", "")) for item in items):
        return
    try:
        from sqlalchemy import event

        from backend.app.db.session import engine
    except Exception as exc:
        _emit(f"{_PREFIX} INSTALL-FAILED t={time.monotonic() - _t0:.3f} error={type(exc).__name__}: {exc}")
        return

    sync_engine = engine.sync_engine
    pool = sync_engine.pool
    event.listen(pool, "checkout", _on_checkout)
    event.listen(pool, "checkin", _on_checkin)
    _installed = True
    try:
        set_capmanager(config.pluginmanager.get_plugin("capturemanager"))
    except Exception:
        set_capmanager(None)

    for item in items:
        if _mapping_node(getattr(item, "nodeid", "")):
            _wrap_test(item)

    plugin_names: list[str] = []
    try:
        for plugin in config.pluginmanager.get_plugins():
            name = config.pluginmanager.get_name(plugin) or type(plugin).__name__
            lowered = name.lower()
            if any(token in lowered for token in ("asyncio", "anyio", "xdist")):
                plugin_names.append(name)
    except Exception:
        plugin_names = ["unavailable"]

    versions: list[str] = []
    for mod_name in ("pytest", "pytest_asyncio", "anyio", "sqlalchemy", "asyncpg", "uvloop"):
        mod = sys.modules.get(mod_name)
        if mod is None:
            try:
                mod = __import__(mod_name)
            except Exception:
                versions.append(f"{mod_name}=absent")
                continue
        versions.append(f"{mod_name}={getattr(mod, '__version__', '?')}")

    worker = os.environ.get("PYTEST_XDIST_WORKER", "absent")
    xdist_loaded = "0"
    try:
        if config.pluginmanager.hasplugin("xdist"):
            xdist_loaded = "1"
    except Exception:
        xdist_loaded = "?"
    order = " | ".join(getattr(item, "nodeid", "") for item in items)
    _emit(
        " ".join(
            [
                _PREFIX,
                "SESSION",
                f"t={time.monotonic() - _t0:.3f}",
                _thread_bits(),
                f"xdist_worker={worker}",
                f"xdist_plugin={xdist_loaded}",
                f"engine={id(engine)}",
                f"sync_engine={id(sync_engine)}",
                f"pool={id(pool)}",
                f"pool_class={type(pool).__name__}",
                f"plugins={','.join(plugin_names) or 'none'}",
                *versions,
                f"collected={len(items)}",
                f"order={order}",
            ]
        )
    )
    config.pluginmanager.register(_Plugin(), "hostflow_async_loop_diag")
