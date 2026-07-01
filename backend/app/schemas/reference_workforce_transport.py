from __future__ import annotations

from pydantic import BaseModel, Field


class WorkforceTransportCodeLabelOut(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)


class ReferenceWorkforceTransportSnapshotOut(BaseModel):
    contract_version: str = Field(min_length=1, max_length=64)
    reference_version: str = Field(min_length=1, max_length=256)
    catalog_version: str = Field(min_length=1, max_length=128)
    workforce_categories: list[WorkforceTransportCodeLabelOut]
    employment_types: list[WorkforceTransportCodeLabelOut]
    transport_modes: list[WorkforceTransportCodeLabelOut]
    transport_qualification_types: list[WorkforceTransportCodeLabelOut]
    driver_capability_classes: list[WorkforceTransportCodeLabelOut]
