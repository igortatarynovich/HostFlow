"""Typed errors for Template Platform domain (PR-1)."""

from __future__ import annotations


class TemplateDomainError(Exception):
    def __init__(self, code: str, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
