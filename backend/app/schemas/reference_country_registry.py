from __future__ import annotations

from pydantic import BaseModel, Field


class CountryIdentityOut(BaseModel):
    alpha2: str = Field(min_length=2, max_length=2)
    alpha3: str = Field(min_length=3, max_length=3)
    numeric: str = Field(min_length=3, max_length=3)


class CountryClassificationsOut(BaseModel):
    dial_code: str = Field(min_length=2, max_length=8)
    eu_member: bool
    schengen_member: bool


class CountryLabelsOut(BaseModel):
    en: str = Field(min_length=1, max_length=128)
    pl: str = Field(min_length=1, max_length=128)
    ru: str = Field(min_length=1, max_length=128)


class CountryRegistryEntryOut(BaseModel):
    identity: CountryIdentityOut
    classifications: CountryClassificationsOut
    labels: CountryLabelsOut


class CountryRegistrySnapshotOut(BaseModel):
    contract_version: str = Field(min_length=1, max_length=64)
    reference_version: str = Field(min_length=1, max_length=256)
    catalog_version: str = Field(min_length=1, max_length=128)
    countries: list[CountryRegistryEntryOut]
