from __future__ import annotations

from pydantic import BaseModel, Field


class RulePackTypeOut(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)


class RulePackMetadataOut(BaseModel):
    pack_code: str = Field(min_length=1, max_length=64)
    pack_type: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=256)
    lifecycle_state: str = Field(min_length=1, max_length=32)


class RulePackDomainTargetOut(BaseModel):
    pack_code: str = Field(min_length=1, max_length=64)
    target_domain: str = Field(min_length=1, max_length=64)


class RulePackVersionMarkerOut(BaseModel):
    pack_code: str = Field(min_length=1, max_length=64)
    schema_version: str = Field(min_length=1, max_length=32)
    compatibility_marker: str = Field(min_length=1, max_length=64)


class ReferenceRulePackFoundationSnapshotOut(BaseModel):
    contract_version: str = Field(min_length=1, max_length=64)
    reference_version: str = Field(min_length=1, max_length=256)
    catalog_version: str = Field(min_length=1, max_length=128)
    rule_pack_types: list[RulePackTypeOut]
    rule_pack_metadata: list[RulePackMetadataOut]
    allowed_target_domains: list[RulePackDomainTargetOut]
    rule_pack_versions: list[RulePackVersionMarkerOut]
