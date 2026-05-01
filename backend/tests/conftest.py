from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest
import pytest_asyncio
import sqlalchemy as sa
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"

os.environ["JWT_SECRET"] = os.environ.get("JWT_SECRET", "hostflow-dev-secret")
os.environ["ALLOW_SQLITE_FOR_TESTS"] = "0"
os.environ["DOCUMENTS_DISABLED"] = "0"
os.environ.setdefault("DEV_DB_PATH", "/tmp/hostflow-test.db")
# Avoid communications_scheduler_loop during ASGI lifespan (slow/teardown TimeoutError on dev DB).
os.environ.setdefault("COMM_SCHEDULER_ENABLED", "0")
# One connection per checkout: avoids asyncpg pool vs pytest-asyncio loop mismatch (Connection._cancel warnings).
os.environ.setdefault("HOSTFLOW_SQLALCHEMY_NULL_POOL", "1")


def _pytest_localize_postgres_host() -> None:
    """Compose uses hostname `db`; on the dev host it often does not resolve (gaierror).

    Rewrite ASYNC_DATABASE_URL / SYNC_DATABASE_URL / DATABASE_URL before any backend import
    that builds the engine. Override with HOSTFLOW_TEST_DB_HOST or PYTEST_DB_HOST if needed.
    """
    import re
    import socket
    from pathlib import Path

    try:
        from dotenv import load_dotenv

        _root = Path(__file__).resolve().parents[2]
        load_dotenv(_root / ".env", override=False)
        load_dotenv(_root / "backend" / ".env", override=False)
    except Exception:
        pass

    keys = ("ASYNC_DATABASE_URL", "SYNC_DATABASE_URL", "DATABASE_URL")
    override = (os.environ.get("HOSTFLOW_TEST_DB_HOST") or os.environ.get("PYTEST_DB_HOST") or "").strip()
    if override:
        for key in keys:
            val = os.environ.get(key)
            if val and "@db:" in val:
                os.environ[key] = re.sub(r"@db:", f"@{override}:", val)
        return

    try:
        socket.getaddrinfo("db", 5432, type=socket.SOCK_STREAM)
        return
    except OSError:
        pass

    for key in keys:
        val = os.environ.get(key)
        if val and "@db:" in val:
            os.environ[key] = re.sub(r"@db:", "@127.0.0.1:", val)


_pytest_localize_postgres_host()


def _alembic_executable(repo_root: Path) -> str | None:
    for rel in (".venv/bin/alembic", ".venv312/bin/alembic"):
        p = repo_root / rel
        if p.is_file():
            return str(p)
    import shutil

    return shutil.which("alembic")


def _env_with_local_db_host(base: dict[str, str]) -> dict[str, str]:
    """Subprocess may run before app settings; mirror conftest @db → 127.0.0.1 rewrite."""
    import re

    out = dict(base)
    for key in ("ALEMBIC_DATABASE_URL", "SYNC_DATABASE_URL", "DATABASE_URL", "ASYNC_DATABASE_URL"):
        val = out.get(key)
        if val and "@db:" in val:
            out[key] = re.sub(r"@db:", "@127.0.0.1:", val)
    return out


def pytest_sessionstart(session: pytest.Session) -> None:
    """Apply Alembic migrations so ORM columns (e.g. FTS tsvector) exist on the test DB."""
    if os.environ.get("HOSTFLOW_SKIP_ALEMBIC_UPGRADE", "").strip().lower() in ("1", "true", "yes"):
        return
    backend_root = Path(__file__).resolve().parents[1]
    repo_root = Path(__file__).resolve().parents[2]
    alembic_ini = backend_root / "alembic.ini"
    if not alembic_ini.is_file():
        return
    url = (
        os.environ.get("ALEMBIC_DATABASE_URL")
        or os.environ.get("SYNC_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    )
    if not url or url.startswith("sqlite:"):
        return
    alembic_bin = _alembic_executable(repo_root)
    if not alembic_bin:
        raise RuntimeError(
            "Alembic executable not found (.venv/bin/alembic). Run `make install` or set HOSTFLOW_SKIP_ALEMBIC_UPGRADE=1."
        )
    subprocess.run(
        [alembic_bin, "-c", str(alembic_ini), "upgrade", "head"],
        cwd=str(backend_root),
        check=True,
        env=_env_with_local_db_host(os.environ),
    )


from backend.app.auth.jwt_tools import encode as encode_jwt  # noqa: E402
from backend.app.core.security import hash_password  # noqa: E402
from backend.app.db.session import async_session_maker  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models.user import Role as UserRole  # noqa: E402
from backend.app.models.user import User  # noqa: E402
from backend.app.models import Candidate  # noqa: E402
from backend.app.models.tenant import TenantLicense  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


_BOOTSTRAP: Dict[str, str] = {}
_BOOTSTRAP_LOCK = asyncio.Lock()


async def _set_tenant(session, tenant_id: str) -> None:
    """
    Ensure Postgres session carries tenant context for RLS-aware queries.
    """
    try:
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )
    except Exception:
        pass


async def _init_data() -> Dict[str, str]:
    """Initialise minimal data set for integration tests (idempotent)."""
    if _BOOTSTRAP:
        return _BOOTSTRAP

    async with _BOOTSTRAP_LOCK:
        if _BOOTSTRAP:
            return _BOOTSTRAP

        admin_email = "biuro@work-host.com"
        admin_password = "Host123!"
        viewer_email = "viewer@work-host.com"
        viewer_password = "Viewer123!"
        supervisor_email = "supervisor@work-host.com"
        supervisor_password = "Supervisor123!"
        recruiter_email = "recruiter@work-host.com"
        recruiter_password = "Recruiter123!"
        hr_officer_email = "hr.officer@work-host.com"
        hr_officer_password = "HrOfficer123!"

        candidate_id: str | None = None

        async with async_session_maker() as session:
            await _set_tenant(session, DEFAULT_TENANT_ID)

            admin = await session.scalar(
                select(User).where(func.lower(User.email) == admin_email.lower())
            )
            if admin is None:
                admin = User(
                    id=str(uuid.uuid4()),
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    role=UserRole.administrator,
                    short_id="ADMIN001",
                    full_name="HostFlow Admin",
                    tenant_id=DEFAULT_TENANT_ID,
                    is_active=True,
                )
                session.add(admin)
            else:
                admin.password_hash = hash_password(admin_password)
                admin.role = UserRole.administrator
                admin.short_id = admin.short_id or "ADMIN001"
                admin.full_name = admin.full_name or "HostFlow Admin"
                admin.tenant_id = admin.tenant_id or DEFAULT_TENANT_ID
                admin.is_active = True

            viewer = await session.scalar(
                select(User).where(func.lower(User.email) == viewer_email.lower())
            )
            if viewer is None:
                viewer = User(
                    id=str(uuid.uuid4()),
                    email=viewer_email,
                    password_hash=hash_password(viewer_password),
                    role=UserRole.viewer,
                    short_id="VIEWR001",
                    full_name="HostFlow Viewer",
                    tenant_id=DEFAULT_TENANT_ID,
                    is_active=True,
                )
                session.add(viewer)
            else:
                viewer.password_hash = hash_password(viewer_password)
                viewer.role = UserRole.viewer
                viewer.short_id = viewer.short_id or "VIEWR001"
                viewer.full_name = viewer.full_name or "HostFlow Viewer"
                viewer.tenant_id = viewer.tenant_id or DEFAULT_TENANT_ID
                viewer.is_active = True

            supervisor = await session.scalar(
                select(User).where(func.lower(User.email) == supervisor_email.lower())
            )
            if supervisor is None:
                supervisor = User(
                    id=str(uuid.uuid4()),
                    email=supervisor_email,
                    password_hash=hash_password(supervisor_password),
                    role=UserRole.supervisor,
                    short_id="SUPV001",
                    full_name="HostFlow Supervisor",
                    tenant_id=DEFAULT_TENANT_ID,
                    is_active=True,
                )
                session.add(supervisor)
            else:
                supervisor.password_hash = hash_password(supervisor_password)
                supervisor.role = UserRole.supervisor
                supervisor.short_id = supervisor.short_id or "SUPV001"
                supervisor.full_name = supervisor.full_name or "HostFlow Supervisor"
                supervisor.tenant_id = supervisor.tenant_id or DEFAULT_TENANT_ID
                supervisor.is_active = True

            recruiter = await session.scalar(
                select(User).where(func.lower(User.email) == recruiter_email.lower())
            )
            if recruiter is None:
                recruiter = User(
                    id=str(uuid.uuid4()),
                    email=recruiter_email,
                    password_hash=hash_password(recruiter_password),
                    role=UserRole.recruiter,
                    short_id="REC001",
                    full_name="HostFlow Recruiter",
                    tenant_id=DEFAULT_TENANT_ID,
                    supervisor_id=supervisor.id,
                    is_active=True,
                )
                session.add(recruiter)
            else:
                recruiter.password_hash = hash_password(recruiter_password)
                recruiter.role = UserRole.recruiter
                recruiter.short_id = recruiter.short_id or "REC001"
                recruiter.full_name = recruiter.full_name or "HostFlow Recruiter"
                recruiter.tenant_id = recruiter.tenant_id or DEFAULT_TENANT_ID
                recruiter.is_active = True
                recruiter.supervisor_id = supervisor.id

            hr_officer = await session.scalar(
                select(User).where(func.lower(User.email) == hr_officer_email.lower())
            )
            if hr_officer is None:
                hr_officer = User(
                    id=str(uuid.uuid4()),
                    email=hr_officer_email,
                    password_hash=hash_password(hr_officer_password),
                    role=UserRole.hr_officer,
                    short_id="HROFF001",
                    full_name="HostFlow HR Officer",
                    tenant_id=DEFAULT_TENANT_ID,
                    is_active=True,
                )
                session.add(hr_officer)
            else:
                hr_officer.password_hash = hash_password(hr_officer_password)
                hr_officer.role = UserRole.hr_officer
                hr_officer.short_id = hr_officer.short_id or "HROFF001"
                hr_officer.full_name = hr_officer.full_name or "HostFlow HR Officer"
                hr_officer.tenant_id = hr_officer.tenant_id or DEFAULT_TENANT_ID
                hr_officer.is_active = True

            await session.flush()

            async def ensure_membership(user_id: str, role: str) -> None:
                await session.execute(
                    sa.text(
                        """
                        INSERT INTO user_memberships (id, user_id, tenant_id, role)
                        VALUES (:id, :user_id, :tenant_id, :role)
                        ON CONFLICT(user_id, tenant_id)
                        DO UPDATE SET role = excluded.role
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "tenant_id": DEFAULT_TENANT_ID,
                        "role": role,
                    },
                )

            await ensure_membership(admin.id, "administrator")
            await ensure_membership(viewer.id, "viewer")
            await ensure_membership(supervisor.id, "supervisor")
            await ensure_membership(recruiter.id, "recruiter")
            await ensure_membership(hr_officer.id, "hr_officer")

            result = await session.execute(
                sa.text(
                    "SELECT id FROM companies WHERE tenant_id = :tenant LIMIT 1"
                ),
                {"tenant": DEFAULT_TENANT_ID},
            )
            company_id = result.scalar_one_or_none()
            if company_id is None:
                company_id = str(uuid.uuid4())
                await session.execute(
                    sa.text(
                        "INSERT INTO companies (id, tenant_id, name) VALUES (:id, :tenant_id, :name)"
                    ),
                    {
                        "id": company_id,
                        "tenant_id": DEFAULT_TENANT_ID,
                        "name": "Test Logistics Sp. z o.o.",
                    },
                )

            await session.execute(
                sa.text(
                    """
                    INSERT INTO user_company_access (id, tenant_id, user_id, company_id, can_edit)
                    VALUES (:id, :tenant_id, :user_id, :company_id, :can_edit)
                    ON CONFLICT(tenant_id, user_id, company_id)
                    DO UPDATE SET can_edit = excluded.can_edit
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": DEFAULT_TENANT_ID,
                    "user_id": recruiter.id,
                    "company_id": company_id,
                    "can_edit": True,
                },
            )

            candidate_row = await session.execute(
                sa.text(
                    "SELECT id FROM candidates WHERE tenant_id = :tenant LIMIT 1"
                ),
                {"tenant": DEFAULT_TENANT_ID},
            )
            candidate_id = candidate_row.scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if candidate_id is None:
                candidate_id = str(uuid.uuid4())
                await session.execute(
                    sa.text(
                        """
                        INSERT INTO candidates (id, tenant_id, first_name, last_name, manager, company_id, created_at, updated_at)
                        VALUES (:id, :tenant_id, :first_name, :last_name, :manager, :company_id, :created_at, :updated_at)
                        """
                    ),
                    {
                        "id": candidate_id,
                        "tenant_id": DEFAULT_TENANT_ID,
                        "first_name": "Piotr",
                        "last_name": "Lis",
                        "manager": recruiter.id,
                        "company_id": company_id,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
            else:
                await session.execute(
                    sa.text(
                        "UPDATE candidates SET manager = :manager, company_id = :company_id WHERE id = :id"
                    ),
                    {"manager": recruiter.id, "company_id": company_id, "id": candidate_id},
                )

            # Shared dev DB may seed tenant_licenses with finite caps; vacancy API then returns 402.
            lic_row = await session.execute(
                select(TenantLicense).where(TenantLicense.tenant_id == DEFAULT_TENANT_ID).limit(1)
            )
            lic = lic_row.scalar_one_or_none()
            if lic is not None:
                lic.max_vacancies_active = 0
                lic.max_candidates_active = 0

            await session.commit()

        _BOOTSTRAP.update(
            {
                "tenant_id": DEFAULT_TENANT_ID,
                "admin_id": admin.id,
                "admin_email": admin.email,
                "viewer_id": viewer.id,
                "viewer_email": viewer.email,
                "supervisor_id": supervisor.id,
                "supervisor_email": supervisor.email,
                "recruiter_id": recruiter.id,
                "recruiter_email": recruiter.email,
                "hr_officer_id": hr_officer.id,
                "hr_officer_email": hr_officer.email,
                "company_id": company_id,
                "candidate_id": candidate_id,
            }
        )

    return _BOOTSTRAP


def _build_token(user_id: str, email: str, role: str, tenant_id: str, supervisor_id: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=120)).timestamp()),
    }
    if supervisor_id:
        payload["supervisor_id"] = supervisor_id
    return encode_jwt(payload)


@pytest_asyncio.fixture
async def db():
    """Async DB session for unit tests (e.g. audit, services)."""
    await _init_data()
    async with async_session_maker() as session:
        await _set_tenant(session, DEFAULT_TENANT_ID)
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """
    In-memory HTTP client bound to FastAPI app with lifespan triggers.
    """
    async with LifespanManager(app):
        await _init_data()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c


@pytest_asyncio.fixture
async def app_with_db() -> AsyncClient:
    async with LifespanManager(app):
        await _init_data()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c


@pytest_asyncio.fixture
async def tenant_id() -> str:
    data = await _init_data()
    return data["tenant_id"]


@pytest_asyncio.fixture
async def bootstrap() -> Dict[str, str]:
    """Stable tenant/user/candidate ids from `_init_data()` (same keys across tests)."""
    return await _init_data()


@pytest_asyncio.fixture
async def manager_token(tenant_id: str) -> str:
    data = await _init_data()
    return _build_token(
        data["admin_id"],
        data["admin_email"],
        "administrator",
        tenant_id,
    )


@pytest_asyncio.fixture
async def supervisor_token(tenant_id: str) -> str:
    data = await _init_data()
    return _build_token(
        data["supervisor_id"],
        data["supervisor_email"],
        "supervisor",
        tenant_id,
    )


@pytest_asyncio.fixture
async def recruiter_token(tenant_id: str) -> str:
    data = await _init_data()
    return _build_token(
        data["recruiter_id"],
        data["recruiter_email"],
        "recruiter",
        tenant_id,
        data.get("supervisor_id"),
    )


@pytest_asyncio.fixture
async def hr_officer_token(tenant_id: str) -> str:
    data = await _init_data()
    return _build_token(
        data["hr_officer_id"],
        data["hr_officer_email"],
        "hr_officer",
        tenant_id,
    )


@pytest_asyncio.fixture
async def viewer_token(tenant_id: str) -> str:
    data = await _init_data()
    return _build_token(
        data["viewer_id"],
        data["viewer_email"],
        "viewer",
        tenant_id,
    )


@pytest_asyncio.fixture
async def manager_headers(manager_token: str, tenant_id: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {manager_token}",
        "X-Tenant-Id": tenant_id,
    }


@pytest_asyncio.fixture
async def supervisor_headers(supervisor_token: str, tenant_id: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {supervisor_token}",
        "X-Tenant-Id": tenant_id,
    }


@pytest_asyncio.fixture
async def recruiter_headers(recruiter_token: str, tenant_id: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {recruiter_token}",
        "X-Tenant-Id": tenant_id,
    }


@pytest_asyncio.fixture
async def hr_officer_headers(hr_officer_token: str, tenant_id: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {hr_officer_token}",
        "X-Tenant-Id": tenant_id,
    }


@pytest_asyncio.fixture
async def viewer_headers(viewer_token: str, tenant_id: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {viewer_token}",
        "X-Tenant-Id": tenant_id,
    }


@pytest.fixture
def auth_headers(manager_token: str, tenant_id: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {manager_token}",
        "X-Tenant-Id": tenant_id,
    }


@pytest_asyncio.fixture
async def candidate_id() -> str:
    data = await _init_data()
    candidate_id = str(uuid.uuid4())
    # Candidate.created_at/updated_at are naive UTC columns.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with async_session_maker() as session:
        await _set_tenant(session, data["tenant_id"])
        candidate = Candidate(
            id=candidate_id,
            tenant_id=data["tenant_id"],
            first_name=f"Test{candidate_id[:4]}",
            last_name="Candidate",
            email=f"candidate_{candidate_id[:4]}@example.com",
            stage="new",
            manager=data["recruiter_id"],
            company_id=data["company_id"],
            created_at=now,
            updated_at=now,
        )
        session.add(candidate)
        await session.commit()
    return candidate_id
