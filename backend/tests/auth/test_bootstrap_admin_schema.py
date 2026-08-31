"""OL-2B: fresh-schema bootstrap admin and seed idempotency.

``superadmin`` is a persisted ADR-036 trust role, not a seed-only label.
``users.preferences`` is NOT NULL with an empty-object default — any INSERT
that omits the column must receive ``{}``.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.auth import ensure_seed
from backend.app.db.session import async_session_maker
from backend.app.models.user import Role


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@hostflow.test"


@pytest.mark.anyio
async def test_role_enum_includes_superadmin() -> None:
    async with async_session_maker() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("native role enum is PostgreSQL only")
        labels = {
            row[0]
            for row in (
                await session.execute(
                    text(
                        "SELECT e.enumlabel FROM pg_enum e "
                        "JOIN pg_type t ON t.oid = e.enumtypid "
                        "WHERE t.typname = 'role'"
                    )
                )
            ).all()
        }
    assert Role.superadmin.value in labels
    assert {Role.administrator.value, Role.employee.value, Role.viewer.value} <= labels


@pytest.mark.anyio
async def test_preferences_server_default_is_empty_object() -> None:
    async with async_session_maker() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("PostgreSQL only")
        default = (
            await session.execute(
                text(
                    "SELECT column_default FROM information_schema.columns "
                    "WHERE table_name = 'users' AND column_name = 'preferences'"
                )
            )
        ).scalar_one()
        nullable = (
            await session.execute(
                text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'users' AND column_name = 'preferences'"
                )
            )
        ).scalar_one()
    assert nullable == "NO"
    assert default is not None
    assert "{}" in str(default)


@pytest.mark.anyio
async def test_raw_insert_superadmin_omitting_preferences() -> None:
    """The seed's historical INSERT shape (no preferences column) must succeed."""
    user_id = str(uuid.uuid4())
    email = _unique_email("ol2b-raw")
    async with async_session_maker() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("PostgreSQL only")
        await session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role, tenant_id, is_active) "
                "VALUES (:id, :email, :password_hash, :role, :tenant_id, true)"
            ),
            {
                "id": user_id,
                "email": email,
                "password_hash": "x",
                "role": Role.superadmin.value,
                "tenant_id": ensure_seed.DEFAULT_TENANT_ID,
            },
        )
        await session.commit()
        row = (
            await session.execute(
                text("SELECT role::text, preferences FROM users WHERE id = :id"),
                {"id": user_id},
            )
        ).one()
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await session.commit()
    assert row[0] == Role.superadmin.value
    assert row[1] == {}


@pytest.mark.anyio
async def test_ensure_auth_seed_creates_admin_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_email = _unique_email("ol2b-seed-admin")
    hr_email = _unique_email("ol2b-seed-hr")
    monkeypatch.setenv("HOSTFLOW_AUTH_SEED_ENABLED", "1")
    monkeypatch.setattr(ensure_seed, "ADMIN_EMAIL", admin_email)
    monkeypatch.setattr(ensure_seed, "HR_OFFICER_EMAIL", hr_email)

    await ensure_seed.ensure_auth_seed()
    await ensure_seed.ensure_auth_seed()

    async with async_session_maker() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("PostgreSQL only")
        rows = (
            await session.execute(
                text(
                    "SELECT email, role::text, preferences IS NOT NULL AS has_prefs "
                    "FROM users WHERE email IN (:admin, :hr) ORDER BY email"
                ),
                {"admin": admin_email, "hr": hr_email},
            )
        ).all()
        await session.execute(
            text("DELETE FROM user_memberships WHERE user_id IN (SELECT id FROM users WHERE email IN (:admin, :hr))"),
            {"admin": admin_email, "hr": hr_email},
        )
        await session.execute(
            text("DELETE FROM users WHERE email IN (:admin, :hr)"),
            {"admin": admin_email, "hr": hr_email},
        )
        await session.commit()

    emails = [r[0] for r in rows]
    assert emails.count(admin_email) == 1
    admin = next(r for r in rows if r[0] == admin_email)
    assert admin[1] == Role.superadmin.value
    assert admin[2] is True


@pytest.mark.anyio
async def test_ensure_auth_seed_raises_when_insert_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOSTFLOW_AUTH_SEED_ENABLED", "1")
    monkeypatch.setattr(ensure_seed, "ADMIN_EMAIL", _unique_email("ol2b-fail"))

    async def _missing(_db, _email: str) -> bool:
        return False

    async def _tables(_db, name: str) -> bool:
        return name == "users"

    async def _cols(_db, _table: str) -> set[str]:
        return {
            "id",
            "email",
            "password_hash",
            "role",
            "is_active",
            "tenant_id",
            "created_at",
            "updated_at",
            "preferences",
        }

    monkeypatch.setattr(ensure_seed, "_user_exists", _missing)
    monkeypatch.setattr(ensure_seed, "_table_exists", _tables)
    monkeypatch.setattr(ensure_seed, "_columns", _cols)

    class _BoomSession:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("forced insert failure")

        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

    class _BoomMaker:
        def __call__(self):
            class _Ctx:
                async def __aenter__(self):
                    return _BoomSession()

                async def __aexit__(self, *args):
                    return False

            return _Ctx()

    monkeypatch.setattr(ensure_seed, "async_session_maker", _BoomMaker())
    with pytest.raises(RuntimeError, match="bootstrap admin insert failed"):
        await ensure_seed.ensure_auth_seed()
