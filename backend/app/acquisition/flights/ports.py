"""Flights destination intake ports — L0 published contracts.

Destination modules implement these ports via inbound adapters.
Flights dispatches against the contract only — never against module ORM.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.flights.destination_contract import (
    DestinationDispatchResult,
    DestinationSubmitRequest,
)


class DestinationIntakePort(Protocol):
    """Inbound port implemented by Recruitment / Sales adapters."""

    async def accept(
        self,
        db: AsyncSession,
        request: DestinationSubmitRequest,
    ) -> DestinationDispatchResult: ...


class RecruitmentIntakePort(DestinationIntakePort, Protocol):
    """Recruitment-owned inbound port for candidate_application."""


class SalesIntakePort(DestinationIntakePort, Protocol):
    """Sales-owned inbound port for sales_inquiry."""
