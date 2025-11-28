"""
Document type definitions and classification helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass
class DocumentTypeInfo:
    """Information about a document type."""
    code: str
    name: str
    keywords: List[str]  # Keywords for classification
    mrz_supported: bool  # Whether MRZ is typically present
    typical_pages: int  # Typical number of pages
    is_passport: bool = False  # Special handling for passports


# Document type definitions
DOCUMENT_TYPES: Dict[str, DocumentTypeInfo] = {
    "passport": DocumentTypeInfo(
        code="passport",
        name="Passport",
        keywords=["passport", "паспорт", "passeport", "paszport", "pass", "passport no", "passport number"],
        mrz_supported=True,
        typical_pages=26,
        is_passport=True,
    ),
    "identity_document": DocumentTypeInfo(
        code="identity_document",
        name="Identity Document",
        keywords=["id card", "identity", "national id", "dowód osobisty"],
        mrz_supported=False,
        typical_pages=2,
    ),
    "residence_permit": DocumentTypeInfo(
        code="residence_permit",
        name="Residence Permit / Karta pobytu",
        keywords=["karta pobytu", "residence permit", "trc", "temporary residence", "zezwolenie"],
        mrz_supported=True,
        typical_pages=2,
    ),
    "driver_license": DocumentTypeInfo(
        code="driver_license",
        name="Driver License / Prawo jazdy",
        keywords=["prawo jazdy", "driver license", "driving licence", "kierowca", "cat.", "category"],
        mrz_supported=False,
        typical_pages=2,
    ),
    "qualification_card": DocumentTypeInfo(
        code="qualification_card",
        name="Qualification Card / KP",
        keywords=["kp", "karta kwalifikacji", "qualification", "świadectwo kwalifikacji"],
        mrz_supported=False,
        typical_pages=1,
    ),
    "adr_certificate": DocumentTypeInfo(
        code="adr_certificate",
        name="ADR Certificate",
        keywords=["adr", "dangerous goods", "materiały niebezpieczne"],
        mrz_supported=False,
        typical_pages=1,
    ),
    "tachograph_card": DocumentTypeInfo(
        code="tachograph_card",
        name="Tachograph Card / Karta tachografu",
        keywords=["tachograph", "tacho", "tachokarta", "karta tachografu"],
        mrz_supported=False,
        typical_pages=2,
    ),
    "medical_certificate": DocumentTypeInfo(
        code="medical_certificate",
        name="Medical Certificate / Badania lekarskie",
        keywords=["badania lekarskie", "medical", "lekarskie", "certificate", "świadectwo"],
        mrz_supported=False,
        typical_pages=1,
    ),
    "psychological_test": DocumentTypeInfo(
        code="psychological_test",
        name="Psychological Test / Psychotest",
        keywords=["psychologiczne", "psychological", "psychotest", "test psychologiczny"],
        mrz_supported=False,
        typical_pages=1,
    ),
    "decision": DocumentTypeInfo(
        code="decision",
        name="Decision / Decyzja",
        keywords=["decyzja", "decision", "zawiadomienie", "notification"],
        mrz_supported=False,
        typical_pages=1,
    ),
    "visa": DocumentTypeInfo(
        code="visa",
        name="Visa",
        keywords=["visa", "wiza", "entry permit", "zezwolenie na wjazd"],
        mrz_supported=True,
        typical_pages=1,
    ),
}


def get_document_type_info(doc_type: str) -> Optional[DocumentTypeInfo]:
    """Get document type info by code."""
    return DOCUMENT_TYPES.get(doc_type.lower())


def list_document_types() -> List[DocumentTypeInfo]:
    """List all available document types."""
    return list(DOCUMENT_TYPES.values())


def is_passport_type(doc_type: str) -> bool:
    """Check if document type is a passport."""
    info = get_document_type_info(doc_type)
    return info.is_passport if info else False

