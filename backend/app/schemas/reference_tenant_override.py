from __future__ import annotations

from pydantic import BaseModel, Field


class TenantOverrideTypeOut(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)


class TenantOverrideDomainOut(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)


class TenantOverrideRuleOut(BaseModel):
    domain_code: str = Field(min_length=1, max_length=64)
    override_type_code: str = Field(min_length=1, max_length=64)
    allowed: bool
    immutable_reason: str = Field(min_length=1, max_length=256)


class TenantOverlaySchemaContractOut(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=32)
    domain: str = Field(min_length=1, max_length=32)
    override_type: str = Field(min_length=1, max_length=32)
    target_code: str = Field(min_length=1, max_length=32)
    value: str = Field(min_length=1, max_length=32)


class ReferenceTenantOverrideFoundationSnapshotOut(BaseModel):
    contract_version: str = Field(min_length=1, max_length=64)
    reference_version: str = Field(min_length=1, max_length=256)
    catalog_version: str = Field(min_length=1, max_length=128)
    override_types: list[TenantOverrideTypeOut]
    allowed_domains: list[TenantOverrideDomainOut]
    immutable_rules: list[TenantOverrideRuleOut]
    overlay_schema_contract: TenantOverlaySchemaContractOut

