from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from backend.app.models.enums import (
    DocumentDuplicatePolicy,
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
)

DEFAULT_ACCEPT = ["application/pdf", "image/jpeg", "image/png"]
REMINDER_DAYS = [60, 30, 7]
GLARE_THRESHOLD = 0.15

ID_CARD_FRAME = {
    "margin_mm": 2,
    "sharpness": 120,
    "min_fill": 0.7,
    "target_dpi": 300,
    "glare": 0.15,
    "max_skew": 2.0,
    "contrast_ratio": 0.6,
    "min_edge_pixels": 1000,
}

PASSPORT_FRAME = {
    "margin_mm": 3,
    "sharpness": 120,
    "min_fill": 0.7,
    "target_dpi": 300,
    "glare": 0.15,
    "max_skew": 2.0,
    "contrast_ratio": 0.6,
    "min_edge_pixels": 1050,
}

A4_FRAME = {
    "margin_mm": 6,
    "sharpness": 140,
    "min_fill": 0.8,
    "target_dpi": 300,
    "glare": 0.12,
    "max_skew": 1.5,
    "contrast_ratio": 0.65,
    "min_edge_pixels": 1650,
}


def _frame_kwargs(config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "margin_mm": config.get("margin_mm"),
        "sharpness_threshold": config.get("sharpness"),
        "min_fill_ratio": config.get("min_fill"),
        "target_dpi": config.get("target_dpi"),
        "glare_threshold": config.get("glare"),
        "max_skew_deg": config.get("max_skew"),
        "contrast_ratio_min": config.get("contrast_ratio"),
        "min_edge_pixels": config.get("min_edge_pixels"),
    }


def _date_schema() -> Dict[str, Any]:
    return {"type": "string", "format": "date"}


def _object_schema(required: Tuple[str, ...], properties: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "object",
        "required": list(required),
        "properties": properties,
        "additionalProperties": False,
    }


def _expiry_rule(field: str | None) -> Dict[str, Any]:
    if not field:
        return {}
    return {"mode": "field", "field": field, "reminders_days": REMINDER_DAYS}


def _frame(
    preset: str,
    *,
    margin_mm: int = 2,
    aspect_ratio: str | None = None,
    sharpness_threshold: int | None = None,
    min_fill_ratio: float | None = None,
    target_dpi: int | None = None,
    glare_threshold: float | None = None,
    max_skew_deg: float | None = None,
    contrast_ratio_min: float | None = None,
    min_edge_pixels: int | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "preset": preset,
        "edge_detection": True,
        "margin_mm": margin_mm,
        "glare_threshold": glare_threshold if glare_threshold is not None else GLARE_THRESHOLD,
    }
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if sharpness_threshold is not None:
        payload["sharpness_threshold"] = sharpness_threshold
    if min_fill_ratio is not None:
        payload["min_fill_ratio"] = min_fill_ratio
    if target_dpi is not None:
        payload["target_dpi"] = target_dpi
    if max_skew_deg is not None:
        payload["max_skew_deg"] = max_skew_deg
    if contrast_ratio_min is not None:
        payload["contrast_ratio_min"] = contrast_ratio_min
    if min_edge_pixels is not None:
        payload["min_edge_pixels"] = min_edge_pixels
    return payload


def _sides_required(
    preset: str,
    *,
    margin_mm: int = 2,
    sharpness: int = 120,
    min_fill: float = 0.7,
    target_dpi: int = 300,
    glare: float | None = None,
    max_skew: float | None = None,
    contrast_ratio: float | None = None,
    min_edge_pixels: int | None = None,
) -> Dict[str, Any]:
    return {
        "type": "sides",
        "sides": ["front", "back"],
        "sequence_required": True,
        "accept": DEFAULT_ACCEPT,
        "max_files": 2,
        "max_page_size_mb": 10,
        "max_total_mb": 30,
        "frame": _frame(
            preset,
            aspect_ratio="85.6x54",
            margin_mm=margin_mm,
            sharpness_threshold=sharpness,
            min_fill_ratio=min_fill,
            target_dpi=target_dpi,
            glare_threshold=glare,
            max_skew_deg=max_skew,
            contrast_ratio_min=contrast_ratio,
            min_edge_pixels=min_edge_pixels,
        ),
    }


def _paged_required(
    preset: str,
    min_pages: int = 8,
    *,
    margin_mm: int = 3,
    sharpness: int = 120,
    min_fill: float = 0.7,
    target_dpi: int = 300,
    glare: float | None = None,
    max_skew: float | None = None,
    contrast_ratio: float | None = None,
    min_edge_pixels: int | None = None,
) -> Dict[str, Any]:
    return {
        "type": "paged",
        "min_pages": min_pages,
        "sequence_required": True,
        "accept": DEFAULT_ACCEPT,
        "max_page_size_mb": 10,
        "max_total_mb": 30,
        "frame": _frame(
            preset,
            margin_mm=margin_mm,
            sharpness_threshold=sharpness,
            min_fill_ratio=min_fill,
            target_dpi=target_dpi,
            glare_threshold=glare,
            max_skew_deg=max_skew,
            contrast_ratio_min=contrast_ratio,
            min_edge_pixels=min_edge_pixels,
        ),
    }


def _single_required(
    preset: str | None = None,
    *,
    margin_mm: int = 3,
    sharpness: int = 130,
    min_fill: float = 0.75,
    target_dpi: int = 300,
    glare: float | None = None,
    max_skew: float | None = None,
    contrast_ratio: float | None = None,
    min_edge_pixels: int | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "type": "any",
        "min_files": 1,
        "max_files": 1,
        "accept": DEFAULT_ACCEPT,
        "max_page_size_mb": 10,
        "max_total_mb": 30,
    }
    if preset:
        payload["frame"] = _frame(
            preset,
            margin_mm=margin_mm,
            sharpness_threshold=sharpness,
            min_fill_ratio=min_fill,
            target_dpi=target_dpi,
            glare_threshold=glare,
            max_skew_deg=max_skew,
            contrast_ratio_min=contrast_ratio,
            min_edge_pixels=min_edge_pixels,
        )
    return payload


def _any_required(
    *,
    min_files: int = 1,
    max_files: int | None = None,
    preset: str | None = None,
    frame_kwargs: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "type": "any",
        "min_files": min_files,
        "accept": DEFAULT_ACCEPT,
        "max_page_size_mb": 10,
        "max_total_mb": 30,
    }
    if max_files is not None:
        payload["max_files"] = max_files
    if preset:
        payload["frame"] = _frame(preset, **(frame_kwargs or {}))
    return payload


@dataclass(frozen=True)
class DocumentTypeDefinition:
    code: str
    name: str
    title: Dict[str, str]
    kind: DocumentKind
    requested_from: DocumentRequestedFrom
    # Platform Reference Layer canonical code (ref_document_types.code).
    canonical_ref_code: str = "other"
    process_type: DocumentProcessType = DocumentProcessType.none
    metadata_schema: Dict[str, Any] = field(default_factory=dict)
    required_files: Dict[str, Any] = field(default_factory=dict)
    expiry_rule: Dict[str, Any] = field(default_factory=dict)
    duplicate_policy: DocumentDuplicatePolicy = DocumentDuplicatePolicy.one_per_candidate
    orderable: bool = False
    default_expire_in_days: int | None = None
    aliases: Tuple[str, ...] = field(default_factory=tuple)
    owner_summary_weight: int = 0
    i18n_key: str | None = None
    requires_custom_name: bool = False


DRIVER_DOCUMENT_TYPES: Tuple[DocumentTypeDefinition, ...] = (
    DocumentTypeDefinition(
        code="driver_license",
        name="Driver license",
        title={"ru": "Водительское удостоверение", "en": "Driver license"},
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        canonical_ref_code="driver_license",
        metadata_schema=_object_schema(
            ("number", "categories", "issued_by", "issued_at", "expires_at", "country"),
            {
                "number": {"type": "string", "minLength": 3, "maxLength": 32},
                "categories": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["B", "C", "CE", "C1", "C1E", "D", "DE"]},
                    "minItems": 1,
                },
                "issued_by": {"type": "string"},
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
                "country": {"type": "string", "minLength": 2, "maxLength": 2},
            },
        ),
        required_files=_sides_required("id_card", **ID_CARD_FRAME),
        expiry_rule=_expiry_rule("expires_at"),
        default_expire_in_days=1825,
        aliases=("prawo_jazdy", "drivers_license", "driver_licence", "drivers_license_ce"),
        owner_summary_weight=90,
    ),
    DocumentTypeDefinition(
        code="driver_license_code95",
        name="EU driver license with Code 95",
        title={
            "ru": "Права ЕС с кодом 95",
            "en": "EU driver license (with Code 95)",
        },
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        canonical_ref_code="driver_license",
        metadata_schema=_object_schema(
            ("number", "categories", "issued_at", "expires_at", "country"),
            {
                "number": {"type": "string", "minLength": 3, "maxLength": 32},
                "categories": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["B", "C", "CE", "C1", "C1E", "D", "DE"]},
                    "minItems": 1,
                },
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
                "country": {"type": "string", "minLength": 2, "maxLength": 2},
            },
        ),
        required_files=_sides_required("id_card", **ID_CARD_FRAME),
        expiry_rule=_expiry_rule("expires_at"),
        default_expire_in_days=1825,
        aliases=("driver_license_with_code95", "eu_license_code95"),
        owner_summary_weight=88,
    ),
    DocumentTypeDefinition(
        code="code95",
        name="Qualification card (Code 95)",
        title={
            "ru": "Карта квалификации (Code 95)",
            "en": "Qualification card (Code 95)",
        },
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        canonical_ref_code="driver_qualification_card",
        metadata_schema=_object_schema(
            ("number", "issued_by", "issued_at", "expires_at", "country"),
            {
                "number": {"type": "string", "minLength": 3, "maxLength": 32},
                "issued_by": {"type": "string"},
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
                "country": {"type": "string", "minLength": 2, "maxLength": 2},
            },
        ),
        required_files=_sides_required("id_card", **ID_CARD_FRAME),
        expiry_rule=_expiry_rule("expires_at"),
        default_expire_in_days=1825,
        aliases=("qualification_code95", "code_95", "qualification_card"),
        owner_summary_weight=80,
    ),
    DocumentTypeDefinition(
        code="tacho_card",
        name="Tachograph card",
        title={"ru": "Карта тахографа", "en": "Tachograph card"},
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        process_type=DocumentProcessType.tachograph_card,
        canonical_ref_code="tachograph_card",
        metadata_schema=_object_schema(
            ("number", "issued_at", "expires_at", "country"),
            {
                "number": {"type": "string", "minLength": 6, "maxLength": 32},
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
                "country": {"type": "string", "minLength": 2, "maxLength": 2},
            },
        ),
        required_files=_sides_required("id_card", **ID_CARD_FRAME),
        expiry_rule=_expiry_rule("expires_at"),
        default_expire_in_days=1825,
        aliases=("tachograph_card", "karta_tachografu", "tachograph", "card_tacho"),
        owner_summary_weight=70,
    ),
    DocumentTypeDefinition(
        code="national_id",
        name="National ID",
        title={"ru": "Национальный ID", "en": "National ID"},
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        canonical_ref_code="national_identity_card",
        metadata_schema=_object_schema(
            ("number", "country", "issued_at", "expires_at"),
            {
                "number": {"type": "string", "minLength": 3, "maxLength": 32},
                "country": {"type": "string", "minLength": 2, "maxLength": 2},
                "nationality": {"type": "string", "minLength": 2, "maxLength": 2},
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
            },
        ),
        required_files=_sides_required("id_card", **ID_CARD_FRAME),
        expiry_rule=_expiry_rule("expires_at"),
        default_expire_in_days=3650,
        aliases=("identity_document", "id_card", "dowod_osobisty"),
        owner_summary_weight=60,
    ),
    DocumentTypeDefinition(
        code="passport",
        name="Passport",
        title={"ru": "Паспорт", "en": "Passport"},
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        canonical_ref_code="passport",
        metadata_schema=_object_schema(
            ("number", "country", "issued_at", "expires_at"),
            {
                "number": {"type": "string", "minLength": 3, "maxLength": 32},
                "country": {"type": "string", "minLength": 2, "maxLength": 2},
                "nationality": {"type": "string", "minLength": 2, "maxLength": 2},
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
            },
        ),
        required_files=_paged_required("passport", min_pages=8, **PASSPORT_FRAME),
        expiry_rule=_expiry_rule("expires_at"),
        default_expire_in_days=3650,
        aliases=("travel_document", "passport_non_eu"),
        owner_summary_weight=65,
    ),
    DocumentTypeDefinition(
        code="residence_permit",
        name="Residence permit",
        title={"ru": "Вид на жительство", "en": "Residence permit"},
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        process_type=DocumentProcessType.residence_card,
        canonical_ref_code="residence_card",
        metadata_schema=_object_schema(
            ("number", "type", "issued_at", "expires_at", "voivodeship"),
            {
                "number": {"type": "string", "minLength": 3, "maxLength": 64},
                "type": {"type": "string", "enum": ["temporary", "permanent", "blue_card"]},
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
                "voivodeship": {"type": "string"},
            },
        ),
        required_files=_sides_required("id_card", **ID_CARD_FRAME),
        expiry_rule=_expiry_rule("expires_at"),
        default_expire_in_days=730,
        aliases=("residence_card", "karta_pobytu"),
        owner_summary_weight=60,
    ),
    DocumentTypeDefinition(
        code="visa",
        name="Visa",
        title={"ru": "Виза", "en": "Visa"},
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        process_type=DocumentProcessType.visa,
        canonical_ref_code="visa",
        metadata_schema=_object_schema(
            ("number", "type", "issued_at", "expires_at", "country"),
            {
                "number": {"type": "string", "minLength": 3, "maxLength": 32},
                "type": {"type": "string", "enum": ["C", "D"]},
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
                "country": {"type": "string", "minLength": 2, "maxLength": 2},
            },
        ),
        required_files=_any_required(
            min_files=1,
            max_files=2,
            preset="passport",
            frame_kwargs=_frame_kwargs(PASSPORT_FRAME),
        ),
        expiry_rule=_expiry_rule("expires_at"),
        default_expire_in_days=365,
        aliases=("visa_d", "visa_c", "entry_permit", "entry_permit_or_visa"),
        owner_summary_weight=55,
    ),
    DocumentTypeDefinition(
        code="decision",
        name="Voivodeship decision",
        title={"ru": "Децизия воеводы", "en": "Voivodeship decision"},
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        metadata_schema=_object_schema(
            ("issued_at", "voivodeship"),
            {
                "number": {"type": "string", "minLength": 2, "maxLength": 64},
                "issued_at": _date_schema(),
                "voivodeship": {"type": "string"},
            },
        ),
        required_files=_any_required(min_files=1, preset="a4", frame_kwargs=_frame_kwargs(A4_FRAME)),
        duplicate_policy=DocumentDuplicatePolicy.many_allowed,
        aliases=("decyzja", "voivodeship_decision"),
        owner_summary_weight=35,
    ),
    DocumentTypeDefinition(
        code="medical_certificate",
        name="Medical certificate",
        title={"ru": "Медицинская справка", "en": "Medical certificate", "pl": "Orzeczenie lekarskie"},
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        canonical_ref_code="medical_certificate",
        metadata_schema=_object_schema(
            ("issued_at", "expires_at", "clinic"),
            {
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
                "clinic": {"type": "string"},
            },
        ),
        required_files=_single_required("a4", **A4_FRAME),
        expiry_rule=_expiry_rule("expires_at"),
        default_expire_in_days=365,
        aliases=("badania_lekarskie", "medical_cert", "orzeczenie_lekarskie", "orzeczenie", "medical"),
        owner_summary_weight=30,
    ),
    DocumentTypeDefinition(
        code="psych_tests",
        name="Psychological tests",
        title={"ru": "Психологические тесты", "en": "Psychological tests"},
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        canonical_ref_code="psychological_certificate",
        metadata_schema=_object_schema(
            ("issued_at", "expires_at", "center"),
            {
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
                "center": {"type": "string"},
            },
        ),
        required_files=_any_required(min_files=1, max_files=2, preset="a4", frame_kwargs=_frame_kwargs(A4_FRAME)),
        expiry_rule=_expiry_rule("expires_at"),
        default_expire_in_days=365,
        aliases=("psychotest", "psychotests", "psychological_certificate", "psycho_test"),
        owner_summary_weight=25,
    ),
    DocumentTypeDefinition(
        code="adr",
        name="ADR certificate",
        title={"ru": "Свидетельство ADR", "en": "ADR certificate"},
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        metadata_schema=_object_schema(
            ("number", "issued_at", "expires_at", "classes"),
            {
                "number": {"type": "string", "minLength": 3, "maxLength": 64},
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
                "classes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
            },
        ),
        required_files=_sides_required("id_card", **ID_CARD_FRAME),
        expiry_rule=_expiry_rule("expires_at"),
        default_expire_in_days=1825,
        aliases=("adr_certificate", "adr_card"),
        owner_summary_weight=25,
    ),
    DocumentTypeDefinition(
        code="work_permit",
        name="Work permit",
        title={"ru": "Разрешение на работу", "en": "Work permit"},
        kind=DocumentKind.process,
        requested_from=DocumentRequestedFrom.agency,
        process_type=DocumentProcessType.work_permit,
        canonical_ref_code="work_permit",
        metadata_schema=_object_schema(
            ("number", "issued_by", "issued_at", "valid_from", "valid_to"),
            {
                "number": {"type": "string", "minLength": 3, "maxLength": 64},
                "issued_by": {"type": "string"},
                "issued_at": _date_schema(),
                "valid_from": _date_schema(),
                "valid_to": _date_schema(),
            },
        ),
        required_files=_any_required(min_files=0, preset="a4", frame_kwargs=_frame_kwargs(A4_FRAME)),
        expiry_rule=_expiry_rule("valid_to"),
        duplicate_policy=DocumentDuplicatePolicy.one_per_candidate,
        orderable=True,
        aliases=("oswiadczenie", "zezwolenie_a", "work_permit_support"),
        owner_summary_weight=80,
    ),
    DocumentTypeDefinition(
        code="driver_certificate",
        name="Driver certificate",
        title={"ru": "Świadectwo kierowcy", "en": "Driver certificate"},
        kind=DocumentKind.process,
        requested_from=DocumentRequestedFrom.agency,
        process_type=DocumentProcessType.swiadectwo_kierowcy,
        metadata_schema=_object_schema(
            ("number", "issued_by", "issued_at", "valid_to"),
            {
                "number": {"type": "string", "minLength": 3, "maxLength": 64},
                "issued_by": {"type": "string"},
                "issued_at": _date_schema(),
                "valid_to": _date_schema(),
            },
        ),
        required_files=_any_required(min_files=0, preset="a4", frame_kwargs=_frame_kwargs(A4_FRAME)),
        expiry_rule=_expiry_rule("valid_to"),
        orderable=True,
        aliases=("swiadectwo_kierowcy", "driver_attestation"),
        owner_summary_weight=60,
    ),
    DocumentTypeDefinition(
        code="additional_document",
        name="Additional document",
        title={"ru": "Прочий документ", "en": "Additional document"},
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        metadata_schema=_object_schema(
            ("title", "description"),
            {
                "title": {"type": "string", "minLength": 3, "maxLength": 120},
                "description": {"type": "string", "minLength": 3, "maxLength": 500},
                "issued_at": _date_schema(),
                "expires_at": _date_schema(),
            },
        ),
        required_files=_any_required(min_files=1),
        duplicate_policy=DocumentDuplicatePolicy.many_allowed,
        requires_custom_name=True,
        canonical_ref_code="other",
        aliases=("other", "translation"),
        owner_summary_weight=10,
    ),
)


DOCUMENT_TYPE_DEFINITIONS: Tuple[DocumentTypeDefinition, ...] = DRIVER_DOCUMENT_TYPES
