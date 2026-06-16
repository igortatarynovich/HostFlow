from __future__ import annotations

from pydantic import BaseModel, Field


class ReferenceFieldSchemaOut(BaseModel):
    field_key: str = Field(min_length=1, max_length=64)
    field_type: str = Field(min_length=1, max_length=64)
    group: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=256)
    reference_domain: str = Field(min_length=1, max_length=64)


class ReferenceFieldSchemaSnapshotOut(BaseModel):
    contract_version: str = Field(min_length=1, max_length=64)
    reference_version: str = Field(min_length=1, max_length=256)
    catalog_version: str = Field(min_length=1, max_length=128)
    fields: list[ReferenceFieldSchemaOut]
