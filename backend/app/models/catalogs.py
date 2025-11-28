from __future__ import annotations

from typing import cast

from sqlalchemy import String
from sqlalchemy import cast as sa_cast
from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement

from .user import User

# backend/app/models/catalogs.py



__all__ = ["user_label_expr", "user_short_expr", "user_full_name_expr"]


def user_full_name_expr() -> ColumnElement[str]:
    return cast(ColumnElement[str], User.full_name)


def user_short_expr() -> ColumnElement[str]:
    return cast(ColumnElement[str], User.short_id)


def user_label_expr() -> ColumnElement[str]:
    # COALESCE(full_name, short_id, email)
    return sa_cast(
        func.coalesce(
            user_full_name_expr(),
            user_short_expr(),
            User.email,
        ),
        String,
    )
