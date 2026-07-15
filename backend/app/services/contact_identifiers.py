"""Canonical contact identifier normalization for intake matching (ADR-022)."""

from __future__ import annotations

import re
from typing import Optional


def normalize_email(value: Optional[str]) -> Optional[str]:
    if not value or not str(value).strip():
        return None
    return str(value).strip().lower()


def normalize_phone_digits(value: Optional[str]) -> Optional[str]:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) < 7:
        return None
    return digits[-11:] if len(digits) > 11 else digits


def digits_only(value: Optional[str]) -> str:
    return re.sub(r"\D", "", str(value or ""))
