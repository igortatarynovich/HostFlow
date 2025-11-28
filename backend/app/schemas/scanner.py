from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ScanPresetSchema(BaseModel):
    code: str
    name: str
    aspect_ratio: float
    expected_pages: List[str]
    min_resolution_width: int
    min_resolution_height: int
    max_angle_deviation_deg: float
    min_brightness: float
    max_brightness: float
    min_sharpness: float
    target_width: int


class ScanPageSchema(BaseModel):
    id: str
    page_code: str
    status: str
    quality_score: Optional[float] = None
    issues: List[str] = Field(default_factory=list)
    rotation: int = 0
    applied_filter: Optional[str] = None
    preview_url: Optional[str] = None
    original_url: Optional[str] = None


class ScanSessionSchema(BaseModel):
    id: str
    candidate_id: str
    document_type: str
    document_kind_id: Optional[str] = None
    preset_code: str
    status: str
    expected_pages: List[str]
    pages: List[ScanPageSchema]
    quality_summary: dict = Field(default_factory=dict)
    processed_at: Optional[datetime] = None
    attached_at: Optional[datetime] = None
    failed_reason: Optional[str] = None
    can_attach_to_candidate: bool = False
    upload_limits: dict


class ScanSessionCreateInternal(BaseModel):
    candidate_id: str
    document_type: str
    preset_code: Optional[str] = None  # Auto-selected from document_type if not provided
    document_kind_id: Optional[str] = None
    expected_pages: Optional[List[str]] = None
    meta: Optional[dict] = None


class ScanSessionCreatePublic(BaseModel):
    token: str
    document_type: str
    preset_code: Optional[str] = None
    document_kind_id: Optional[str] = None
    expected_pages: Optional[List[str]] = None
    meta: Optional[dict] = None


class ScanPageUploadResponse(ScanSessionSchema):
    pass


class ScanAttachResponse(BaseModel):
    attached_documents: List[dict]

