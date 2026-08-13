#!/usr/bin/env python3
"""
Создать (или донастроить) пользователя для Focus Personnel с доступом к компании POLTRAKT.

Лиды и кандидаты видны в том тенанте, где у пользователя membership и company access.
Скрипт вызывает тот же create_user, что и API настроек пользователей (хеш пароля, квоты ролей).

Готовая команда (канонические ID уже совпадают с дефолтами скрипта; можно не указывать
``--tenant-id`` / ``--company-id``, если не менялись в БД):

  cd /opt/HostFlow
  python3 backend/scripts/focus_poltrakt_provision_user.py \\
    --tenant-id 9497fc29-6051-424d-9344-abb4aed9b110 \\
    --company-id 2b1ca966-e77d-4a45-9fa6-33ef4c7c2cd5 \\
    --email "osp@poltrakt.pl" \\
    --password 'ЗАМЕНИТЕ_НА_СВОЙ_ПАРОЛЬ' \\
    --full-name "POLTRAKT"

  # Короче (те же tenant/company по умолчанию):
  python3 backend/scripts/focus_poltrakt_provision_user.py \\
    --email "osp@poltrakt.pl" \\
    --password 'ЗАМЕНИТЕ_НА_СВОЙ_ПАРОЛЬ' \\
    --full-name "POLTRAKT"

  # Сгенерировать пароль автоматически
  python3 backend/scripts/focus_poltrakt_provision_user.py --email "osp@poltrakt.pl" --full-name "POLTRAKT"

  # Рекрутер — нужен супервайзер в Focus
  python3 backend/scripts/focus_poltrakt_provision_user.py \\
    --email "rek@poltrakt.pl" --role recruiter --supervisor-id <uuid-супервайзера-в-Focus>

Перед запуском: DATABASE_URL / ASYNC_DATABASE_URL как у backend; на тенанте Focus должна быть лицензия
и свободные слоты под выбранную роль (иначе UserServiceError).

Канонические UUID (как в migrate_poltrakt_company_to_focus.sql): Focus tenant
``9497fc29-6051-424d-9344-abb4aed9b110``, POLTRAKT company ``2b1ca966-e77d-4a45-9fa6-33ef4c7c2cd5``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

THIS = Path(__file__).resolve()
if THIS.parent.name == "scripts" and THIS.parent.parent.name == "backend":
    BACKEND_DIR = THIS.parent.parent
    PROJECT_ROOT = BACKEND_DIR.parent
else:
    PROJECT_ROOT = THIS.parent.parent
    BACKEND_DIR = PROJECT_ROOT / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from backend.app.constants.hostflow_canonical_tenants import (  # noqa: E402
    FOCUS_PERSONNEL_TENANT_ID,
)
from backend.app.core.settings import settings  # noqa: F401, E402
from backend.app.db.session import async_session_maker  # noqa: E402
from backend.app.models.user import User  # noqa: E402
from backend.app.services import users as users_service  # noqa: E402
from backend.app.services.users import UserServiceError  # noqa: E402

DEFAULT_FOCUS_TENANT_ID = FOCUS_PERSONNEL_TENANT_ID
DEFAULT_POLTRAKT_COMPANY_ID = "2b1ca966-e77d-4a45-9fa6-33ef4c7c2cd5"


async def _run(args: argparse.Namespace) -> int:
    async with async_session_maker() as db:
        try:
            entry, tmp_password = await users_service.create_user(
                db,
                tenant_id=args.tenant_id,
                actor_id=None,
                email=args.email,
                role=args.role,
                full_name=(args.full_name or "").strip() or None,
                short_id=None,
                password=args.password,
                supervisor_id=(args.supervisor_id or "").strip() or None,
                company_ids=[args.company_id],
                preset_id=(args.preset_id or "").strip() or None,
            )
            uid = entry["user_id"]
            if args.set_home_tenant:
                user = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
                if user is not None and user.tenant_id != args.tenant_id:
                    user.tenant_id = args.tenant_id
            await db.commit()
        except UserServiceError as exc:
            await db.rollback()
            sys.stderr.write(
                f"[focus-poltrakt-user] UserServiceError ({exc.status_code}): {exc.detail!r}\n"
            )
            return 1
        except Exception as exc:  # pragma: no cover
            await db.rollback()
            sys.stderr.write(f"[focus-poltrakt-user] {exc!r}\n")
            return 1

    out = {
        "user_id": entry["user_id"],
        "email": entry["email"],
        "role": entry["role"],
        "tenant_id": args.tenant_id,
        "company_id": args.company_id,
        "temporary_password": tmp_password,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if tmp_password:
        print("\nСохраните сгенерированный пароль (temporary_password); повторно он не показывается.", file=sys.stderr)
    return 0


def main() -> None:
    epilog = f"""
Готовая команда (Focus + POLTRAKT):
  cd /opt/HostFlow && python3 backend/scripts/focus_poltrakt_provision_user.py \\
    --tenant-id {DEFAULT_FOCUS_TENANT_ID} \\
    --company-id {DEFAULT_POLTRAKT_COMPANY_ID} \\
    --email "osp@poltrakt.pl" \\
    --password 'ЗАМЕНИТЕ_НА_СВОЙ_ПАРОЛЬ' \\
    --full-name "POLTRAKT"
"""
    parser = argparse.ArgumentParser(
        description="Provision Focus Personnel user with POLTRAKT company access.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument("--email", required=True, help="Email (логин)")
    parser.add_argument("--password", default=None, help="Пароль; если не задан — сгенерируется")
    parser.add_argument("--full-name", default=None, help="Отображаемое имя")
    parser.add_argument(
        "--role",
        default="employee",
        help="Trust role or legacy alias (default employee). Prefer --preset-id for job title.",
    )
    parser.add_argument(
        "--preset-id",
        default="team_lead",
        help="ADR-036 preset (recruiter|team_lead|hr|compliance|portal_guest)",
    )
    parser.add_argument("--supervisor-id", default=None, help="UUID супервайзера (для preset=recruiter)")
    parser.add_argument("--tenant-id", default=DEFAULT_FOCUS_TENANT_ID, help="Focus Personnel tenant UUID")
    parser.add_argument(
        "--company-id",
        default=DEFAULT_POLTRAKT_COMPANY_ID,
        help="POLTRAKT company UUID",
    )
    parser.add_argument(
        "--no-set-home-tenant",
        action="store_true",
        help="Не менять users.tenant_id на Focus (по умолчанию домашний тенант = Focus)",
    )
    args = parser.parse_args()
    args.set_home_tenant = not args.no_set_home_tenant
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
