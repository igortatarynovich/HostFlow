from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError


class MetaField(BaseModel):
    name: str
    values: List[str] = Field(default_factory=list)


class MetaLeadValue(BaseModel):
    leadgen_id: str
    page_id: Optional[str] = None
    form_id: Optional[str] = None
    ad_id: Optional[str] = None
    field_data: List[MetaField] = Field(default_factory=list)
    graph_error: Optional[str] = None


class MetaChange(BaseModel):
    field: Literal["leadgen"]
    value: MetaLeadValue


class MetaEntry(BaseModel):
    id: Optional[str] = None
    changes: List[MetaChange]


class MetaWebhookIn(BaseModel):
    object: Literal["page"]
    entry: List[MetaEntry]


def _model_validate(model: type[BaseModel], payload: Dict[str, Any]) -> BaseModel:
    if hasattr(model, "model_validate"):
        return model.model_validate(payload)
    return model.parse_obj(payload)


def to_meta_fields(field_data: List[object]) -> List[MetaField]:
    """Convert Graph/Meta field_data payload into MetaField models."""
    items: List[MetaField] = []
    for item in field_data:
        if not isinstance(item, dict):
            continue
        raw_name = item.get("name")
        name = str(raw_name or "").strip()
        if not name:
            continue
        raw_values = item.get("values") or []
        values = [str(v) for v in raw_values if v is not None]
        items.append(MetaField(name=name, values=values))
    return items


def merge_meta_fields(existing: List[MetaField], incoming: List[MetaField]) -> List[MetaField]:
    """
    Merge field_data arrays so the latest values win while keeping original order.
    """
    merged: Dict[str, MetaField] = {}
    order: List[str] = []

    def _add(field: MetaField) -> None:
        key = field.name.strip().lower()
        if not key:
            return
        if key not in merged:
            order.append(key)
        merged[key] = MetaField(name=field.name, values=list(field.values))

    for field in existing:
        _add(field)
    for field in incoming:
        _add(field)

    return [merged[key] for key in order]


def extract_field_data_from_payload(raw_payload: Dict[str, Any], leadgen_id: str) -> List[MetaField]:
    """
    Extract field_data for a specific leadgen_id from a previously stored payload.
    """
    try:
        event = _model_validate(MetaWebhookIn, raw_payload)
    except ValidationError:
        return []
    for entry in event.entry:
        for change in entry.changes:
            if change.field == "leadgen" and change.value.leadgen_id == leadgen_id:
                return [MetaField(name=field.name, values=list(field.values)) for field in change.value.field_data]
    return []
