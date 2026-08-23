from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from backend.app.document_types.registry import normalize_input_doc_type


@dataclass(frozen=True)
class ScannerPreset:
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
    target_width: int = 1600


# Standard document dimensions (mm)
# ID-1 format (credit card size): 85.6 x 53.98 mm
# Passport spread: ~125 x 88 mm
# A4: 210 x 297 mm
# A5: 148 x 210 mm
# Photo 35x45: 35 x 45 mm

PRESETS: Dict[str, ScannerPreset] = {
    # Identity documents (ID cards, residence permits)
    "identity_document": ScannerPreset(
        code="identity_document",
        name="Документ удостоверяющий личность",
        aspect_ratio=1.59,  # ID-1 format
        expected_pages=["front", "back"],
        min_resolution_width=1200,
        min_resolution_height=800,
        max_angle_deviation_deg=10.0,
        min_brightness=0.18,
        max_brightness=0.92,
        min_sharpness=90.0,
    ),
    "id_card": ScannerPreset(
        code="id_card",
        name="ID карта",
        aspect_ratio=1.59,
        expected_pages=["front", "back"],
        min_resolution_width=1200,
        min_resolution_height=800,
        max_angle_deviation_deg=10.0,
        min_brightness=0.18,
        max_brightness=0.92,
        min_sharpness=90.0,
    ),
    "national_id": ScannerPreset(
        code="national_id",
        name="Национальный ID",
        aspect_ratio=1.59,
        expected_pages=["front", "back"],
        min_resolution_width=1200,
        min_resolution_height=800,
        max_angle_deviation_deg=10.0,
        min_brightness=0.18,
        max_brightness=0.92,
        min_sharpness=90.0,
    ),
    "residence_permit": ScannerPreset(
        code="residence_permit",
        name="Карта pobytu",
        aspect_ratio=1.59,
        expected_pages=["front", "back"],
        min_resolution_width=1200,
        min_resolution_height=800,
        max_angle_deviation_deg=10.0,
        min_brightness=0.18,
        max_brightness=0.92,
        min_sharpness=90.0,
    ),
    "residence_card": ScannerPreset(
        code="residence_card",
        name="Карта pobytu",
        aspect_ratio=1.59,
        expected_pages=["front", "back"],
        min_resolution_width=1200,
        min_resolution_height=800,
        max_angle_deviation_deg=10.0,
        min_brightness=0.18,
        max_brightness=0.92,
        min_sharpness=90.0,
    ),
    # Driver licenses
    "driver_license": ScannerPreset(
        code="driver_license",
        name="Водительские права",
        aspect_ratio=1.59,
        expected_pages=["front", "back"],
        min_resolution_width=1200,
        min_resolution_height=800,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=95.0,
    ),
    "driver_license_exchange": ScannerPreset(
        code="driver_license_exchange",
        name="Обмен водительских прав",
        aspect_ratio=1.59,
        expected_pages=["front", "back"],
        min_resolution_width=1200,
        min_resolution_height=800,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=95.0,
    ),
    # Passports
    "passport": ScannerPreset(
        code="passport",
        name="Паспорт — разворот с фото",
        aspect_ratio=1.42,  # ~125/88
        expected_pages=["spread"],
        min_resolution_width=1400,
        min_resolution_height=900,
        max_angle_deviation_deg=8.0,
        min_brightness=0.22,
        max_brightness=0.9,
        min_sharpness=110.0,
        target_width=1800,
    ),
    "passport_main": ScannerPreset(
        code="passport_main",
        name="Паспорт — разворот с фото",
        aspect_ratio=1.42,
        expected_pages=["spread"],
        min_resolution_width=1400,
        min_resolution_height=900,
        max_angle_deviation_deg=8.0,
        min_brightness=0.22,
        max_brightness=0.9,
        min_sharpness=110.0,
        target_width=1800,
    ),
    "passport_all": ScannerPreset(
        code="passport_all",
        name="Паспорт — все страницы",
        aspect_ratio=1.42,
        expected_pages=["spread", "page_2", "page_3", "page_4"],
        min_resolution_width=1400,
        min_resolution_height=900,
        max_angle_deviation_deg=8.0,
        min_brightness=0.22,
        max_brightness=0.9,
        min_sharpness=110.0,
        target_width=1800,
    ),
    # Visas
    "visa": ScannerPreset(
        code="visa",
        name="Виза",
        aspect_ratio=1.59,
        expected_pages=["front", "back"],
        min_resolution_width=1200,
        min_resolution_height=800,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=95.0,
    ),
    # Tachograph
    "tachograph_card": ScannerPreset(
        code="tachograph_card",
        name="Карта тахографа",
        aspect_ratio=1.59,
        expected_pages=["front", "back"],
        min_resolution_width=1100,
        min_resolution_height=750,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=95.0,
    ),
    "tacho_card": ScannerPreset(
        code="tacho_card",
        name="Карта тахографа",
        aspect_ratio=1.59,
        expected_pages=["front", "back"],
        min_resolution_width=1100,
        min_resolution_height=750,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=95.0,
    ),
    # Certificates and qualifications
    "qualification_code95": ScannerPreset(
        code="qualification_code95",
        name="Сертификат Code95",
        aspect_ratio=1.41,  # A5 landscape
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=100.0,
    ),
    "code95": ScannerPreset(
        code="code95",
        name="Code95",
        aspect_ratio=1.41,
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=100.0,
    ),
    "adr_certificate": ScannerPreset(
        code="adr_certificate",
        name="Сертификат ADR",
        aspect_ratio=1.41,
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=100.0,
    ),
    "adr": ScannerPreset(
        code="adr",
        name="Сертификат ADR",
        aspect_ratio=1.41,
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=100.0,
    ),
    "swiadectwo_kierowcy": ScannerPreset(
        code="swiadectwo_kierowcy",
        name="Świadectwo kierowcy",
        aspect_ratio=1.41,
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=100.0,
    ),
    "driver_certificate": ScannerPreset(
        code="driver_certificate",
        name="Свидетельство водителя",
        aspect_ratio=1.41,
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=100.0,
    ),
    # Medical and tests
    "medical_certificate": ScannerPreset(
        code="medical_certificate",
        name="Медицинская справка",
        aspect_ratio=1.41,  # A5 landscape
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=12.0,
        min_brightness=0.18,
        max_brightness=0.9,
        min_sharpness=85.0,
    ),
    "criminal_record": ScannerPreset(
        code="criminal_record",
        name="Справка о несудимости",
        aspect_ratio=1.41,
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=12.0,
        min_brightness=0.18,
        max_brightness=0.9,
        min_sharpness=85.0,
    ),
    "psychology_test": ScannerPreset(
        code="psychology_test",
        name="Психологические тесты",
        aspect_ratio=1.41,
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=12.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=85.0,
    ),
    "psych_tests": ScannerPreset(
        code="psych_tests",
        name="Психологические тесты",
        aspect_ratio=1.41,
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=12.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=85.0,
    ),
    # Work permits and process documents
    "work_permit": ScannerPreset(
        code="work_permit",
        name="Разрешение на работу",
        aspect_ratio=1.41,
        expected_pages=["front", "back"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=100.0,
    ),
    "decision": ScannerPreset(
        code="decision",
        name="Решение / Decision",
        aspect_ratio=1.41,
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=100.0,
    ),
    # A4 documents (contracts, insurance, etc.)
    "contract": ScannerPreset(
        code="contract",
        name="Контракт",
        aspect_ratio=0.707,  # A4 portrait (210/297)
        expected_pages=["page_1", "page_2"],
        min_resolution_width=1600,
        min_resolution_height=2200,
        max_angle_deviation_deg=5.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=120.0,
        target_width=2000,
    ),
    "employment_contract": ScannerPreset(
        code="employment_contract",
        name="Трудовой договор",
        aspect_ratio=0.707,
        expected_pages=["page_1", "page_2"],
        min_resolution_width=1600,
        min_resolution_height=2200,
        max_angle_deviation_deg=5.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=120.0,
        target_width=2000,
    ),
    "insurance": ScannerPreset(
        code="insurance",
        name="Страховка",
        aspect_ratio=0.707,
        expected_pages=["front"],
        min_resolution_width=1600,
        min_resolution_height=2200,
        max_angle_deviation_deg=5.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=120.0,
        target_width=2000,
    ),
    "bhp": ScannerPreset(
        code="bhp",
        name="BHP обучение",
        aspect_ratio=0.707,
        expected_pages=["front"],
        min_resolution_width=1600,
        min_resolution_height=2200,
        max_angle_deviation_deg=5.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=120.0,
        target_width=2000,
    ),
    "assignment": ScannerPreset(
        code="assignment",
        name="Назначение / Assignment",
        aspect_ratio=0.707,
        expected_pages=["front"],
        min_resolution_width=1600,
        min_resolution_height=2200,
        max_angle_deviation_deg=5.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=120.0,
        target_width=2000,
    ),
    "accommodation": ScannerPreset(
        code="accommodation",
        name="Жильё / Accommodation",
        aspect_ratio=0.707,
        expected_pages=["front"],
        min_resolution_width=1600,
        min_resolution_height=2200,
        max_angle_deviation_deg=5.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=120.0,
        target_width=2000,
    ),
    # Bank and other documents
    "bank_account_confirmation": ScannerPreset(
        code="bank_account_confirmation",
        name="Банковская выписка",
        aspect_ratio=0.707,
        expected_pages=["front"],
        min_resolution_width=1600,
        min_resolution_height=2200,
        max_angle_deviation_deg=5.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=120.0,
        target_width=2000,
    ),
    "pesel": ScannerPreset(
        code="pesel",
        name="PESEL",
        aspect_ratio=1.41,  # Usually A5 landscape
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=10.0,
        min_brightness=0.2,
        max_brightness=0.9,
        min_sharpness=100.0,
    ),
    # Photo
    "photo": ScannerPreset(
        code="photo",
        name="Фото 35x45",
        aspect_ratio=0.778,  # 35/45
        expected_pages=["front"],
        min_resolution_width=800,
        min_resolution_height=1000,
        max_angle_deviation_deg=5.0,
        min_brightness=0.25,
        max_brightness=0.85,
        min_sharpness=110.0,
        target_width=1200,
    ),
    "photo_35x45": ScannerPreset(
        code="photo_35x45",
        name="Фото 35x45",
        aspect_ratio=0.778,
        expected_pages=["front"],
        min_resolution_width=800,
        min_resolution_height=1000,
        max_angle_deviation_deg=5.0,
        min_brightness=0.25,
        max_brightness=0.85,
        min_sharpness=110.0,
        target_width=1200,
    ),
    # Default fallback
    "additional_document": ScannerPreset(
        code="additional_document",
        name="Дополнительный документ",
        aspect_ratio=0.707,
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=12.0,
        min_brightness=0.18,
        max_brightness=0.92,
        min_sharpness=85.0,
    ),
    "other": ScannerPreset(
        code="other",
        name="Прочий документ",
        aspect_ratio=0.707,
        expected_pages=["front"],
        min_resolution_width=1400,
        min_resolution_height=1000,
        max_angle_deviation_deg=12.0,
        min_brightness=0.18,
        max_brightness=0.92,
        min_sharpness=85.0,
    ),
}


# Canonical registry codes → scanner preset keys (physical layout), not alias taxonomy.
CANONICAL_TO_PRESET: Dict[str, str] = {
    "national_identity_card": "id_card",
    "driver_qualification_card": "code95",
    "psychological_certificate": "psych_tests",
    "adr_certificate": "adr",
    "driver_attestation": "driver_certificate",
    "unclassified": "additional_document",
}


def get_preset(code: str) -> ScannerPreset:
    preset = PRESETS.get(code)
    if not preset:
        raise KeyError(code)
    return preset


def list_presets() -> List[ScannerPreset]:
    return list(PRESETS.values())


def get_preset_for_doc_type(doc_type: str) -> ScannerPreset:
    """Map document type (doc_type) to scanner preset via alias registry normalization."""
    canonical = normalize_input_doc_type(doc_type)
    preset_code = CANONICAL_TO_PRESET.get(canonical, canonical)

    if preset_code in PRESETS:
        return PRESETS[preset_code]

    if canonical in PRESETS:
        return PRESETS[canonical]

    sorted_keys = sorted(CANONICAL_TO_PRESET.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in canonical or canonical in key:
            mapped = CANONICAL_TO_PRESET[key]
            if mapped in PRESETS:
                return PRESETS[mapped]

    if "additional_document" in PRESETS:
        return PRESETS["additional_document"]
    if "other" in PRESETS:
        return PRESETS["other"]
    if PRESETS:
        return list(PRESETS.values())[0]
    raise ValueError(f"No scanner preset available for document type: {doc_type}")
