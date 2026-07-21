"""Typed errors for Automation Engine domain (C2.2 PR-1)."""

from __future__ import annotations


class AutomationDomainError(Exception):
    def __init__(self, code: str, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
