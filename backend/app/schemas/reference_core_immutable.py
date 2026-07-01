from __future__ import annotations

from pydantic import BaseModel, Field


class CountryImmutableOut(BaseModel):
    code_alpha2: str = Field(min_length=2, max_length=2)
    code_alpha3: str = Field(min_length=3, max_length=3)
    code_numeric: str = Field(min_length=3, max_length=3)
    name: str = Field(min_length=1, max_length=128)


class LanguageImmutableOut(BaseModel):
    code: str = Field(min_length=2, max_length=8)
    name: str = Field(min_length=1, max_length=128)


class CoreImmutableSnapshotOut(BaseModel):
    contract_version: str = Field(min_length=1, max_length=64)
    reference_version: str = Field(min_length=1, max_length=256)
    catalog_version: str = Field(min_length=1, max_length=128)
    countries: list[CountryImmutableOut]
    languages: list[LanguageImmutableOut]
