from __future__ import annotations

import random
import re
from datetime import date, timedelta
from typing import Any, Dict, Tuple

ExtractionResult = Dict[str, Any]


class Extractor:
    def supports(self, doc_type: str, meta_schema: Dict[str, Any]) -> bool:
        return True

    def extract(
        self, file_bytes: bytes, doc_type: str, meta_schema: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, Any]]:
        """return fields, confidences, raw"""
        raise NotImplementedError


class MrzExtractor(Extractor):
    def supports(self, doc_type: str, meta_schema: Dict[str, Any]) -> bool:
        return bool(meta_schema.get("ocr", {}).get("mrz", False))

    def extract(self, file_bytes: bytes, doc_type: str, meta_schema: Dict[str, Any]):
        # Мок MRZ: генерируем реалистичные поля для паспорта
        today = date.today()
        fields = {}
        if doc_type == "passport":
            fields = {
                "number": "PA" + str(random.randint(100000, 999999)),
                "surname": "DOE",
                "given_names": "JOHN",
                "nationality": "PL",
                "date_of_birth": "1990-05-15",
                "sex": "M",
                "issuing_country": "PL",
                "issued_at": (today - timedelta(days=365 * 3)).isoformat(),
                "expires_at": (today + timedelta(days=365 * 2)).isoformat(),
            }
        confidences = {k: 0.98 for k in fields}
        raw = {"source": "mrz_mock", "bytes": len(file_bytes)}
        return fields, confidences, raw


class TemplateExtractor(Extractor):
    def supports(self, doc_type: str, meta_schema: Dict[str, Any]) -> bool:
        hints = meta_schema.get("ocr", {}).get("hints", [])
        return any(
            h in hints for h in ["template_form", "attestation", "medical_certificate"]
        )

    def extract(self, file_bytes: bytes, doc_type: str, meta_schema: Dict[str, Any]):
        today = date.today()
        fields = {}
        if doc_type in {"driver_attestation", "swiadectwo_kierowcy", "driver_certificate"}:
            fields = {
                "attestation_number": f"AT-{random.randint(100000, 999999)}",
                "company_name": "Acme Logistics Sp. z o.o.",
                "issuing_authority": "GITD",
                "issued_at": (today - timedelta(days=200)).isoformat(),
                "expires_at": (today + timedelta(days=165)).isoformat(),
            }
        elif doc_type in {"medical_cert", "medical_certificate"}:
            fields = {
                "certificate_number": f"MC-{random.randint(10000, 99999)}",
                "clinic_name": "Medycyna Pracy Warszawa",
                "issued_at": (today - timedelta(days=100)).isoformat(),
                "expires_at": (today + timedelta(days=265)).isoformat(),
            }
        confidences = {k: 0.9 for k in fields}
        raw = {"source": "template_mock", "bytes": len(file_bytes)}
        return fields, confidences, raw


class GenericOcrExtractor(Extractor):
    def supports(self, doc_type: str, meta_schema: Dict[str, Any]) -> bool:
        return True

    def _generate_by_regex(self, key: str, pattern: str) -> str:
        """Простой генератор строк под типичные regex из наших схем."""
        # Частные случаи — отдаём валидные мок-значения
        if key.lower() == "iban":
            # валидный пример IBAN (PL) из документации
            return "PL61109010140000071219812874"
        # типичные шаблоны
        if (
            re.fullmatch(r"^\^\[0-9\]\{11\}\$$", pattern.replace(" ", ""))
            or pattern == r"^[0-9]{11}$"
        ):
            return "12345678901"  # PESEL-мок
        if pattern == r"^[0-9]{16}$":
            return "1234567890123456"
        if pattern == r"^[A-Z0-9]{6,10}$":
            return "AB123456"
        if pattern == r"^[A-Z0-9-]{5,15}$":
            return "AB-12345"

        # Общий хак: пытаемся вытащить минимальную длину {m,n}
        m = re.search(r"\{(\d+)(?:,(\d+))?\}", pattern)
        length = 8
        if m:
            length = int(m.group(1))
        # Выбираем набор символов по классу
        if "[A-Z0-9]" in pattern:
            return "A" * max(1, length)
        if "[0-9A-Z]" in pattern:
            return "A" * max(1, length)
        if "[0-9]" in pattern:
            return "1" * max(1, length)
        # fallback
        return "VAL"

    def extract(self, file_bytes: bytes, doc_type: str, meta_schema: Dict[str, Any]):
        fields: Dict[str, Any] = {}
        # Заполняем обязательные поля валидными значениями под regex (если есть)
        for key, spec in meta_schema.get("fields", {}).items():
            if not spec.get("required"):
                continue
            t = spec.get("type")
            rgx = spec.get("regex")
            if t == "date":
                fields[key] = date.today().isoformat()
            elif t == "array":
                fields[key] = []
            elif t == "string":
                if rgx:
                    fields[key] = self._generate_by_regex(key, rgx)
                else:
                    fields[key] = f"VAL_{key.upper()}"
            else:
                fields[key] = f"VAL_{key.upper()}"

        confidences = {k: 0.75 for k in fields}
        raw = {"source": "generic_mock", "bytes": len(file_bytes)}
        return fields, confidences, raw
