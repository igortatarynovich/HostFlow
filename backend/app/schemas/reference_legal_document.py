from __future__ import annotations

from pydantic import BaseModel, Field


class CitizenshipOut(BaseModel):
    code_alpha2: str = Field(min_length=2, max_length=2)
    label: str = Field(min_length=1, max_length=128)


class CatalogCodeLabelOut(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)


class DocumentTypeOut(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    category_code: str = Field(min_length=1, max_length=64)
    expiry_track_required: bool


class LegalDocumentSnapshotOut(BaseModel):
    contract_version: str = Field(min_length=1, max_length=64)
    reference_version: str = Field(min_length=1, max_length=256)
    catalog_version: str = Field(min_length=1, max_length=128)
    citizenships: list[CitizenshipOut]
    legal_statuses: list[CatalogCodeLabelOut]
    permit_types: list[CatalogCodeLabelOut]
    visa_types: list[CatalogCodeLabelOut]
    document_categories: list[CatalogCodeLabelOut]
    document_types: list[DocumentTypeOut]
