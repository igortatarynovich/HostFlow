"""Typed errors for Campaign Orchestrator domain (C2.3 PR-1)."""

from __future__ import annotations


class CampaignDomainError(Exception):
    def __init__(self, code: str, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
