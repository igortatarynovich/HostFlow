from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .ocr_extractor import (
    Extractor,
    GenericOcrExtractor,
    MrzExtractor,
    TemplateExtractor,
)
from .validators import ValidationError


class OcrPipeline:
    def __init__(self, extractors: List[Extractor] | None = None) -> None:
        self.extractors = extractors or [
            MrzExtractor(),
            TemplateExtractor(),
            GenericOcrExtractor(),
        ]

    def load_meta_schema(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run(
        self, file_bytes: bytes, doc_type: str, meta_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        conf: Dict[str, float] = {}
        raws: List[Dict[str, Any]] = []

        # 1) Выбираем подходящие экстракторы
        for ex in self.extractors:
            if ex.supports(doc_type, meta_schema):
                f, c, r = ex.extract(file_bytes, doc_type, meta_schema)
                # merge (не перетираем поля с более высокой уверенностью)
                for k, v in f.items():
                    if k not in fields or c.get(k, 0) > conf.get(k, 0):
                        fields[k] = v
                        conf[k] = c.get(k, 0)
                raws.append(r)

        # 2) Нормализация по типам (даты/строки)
        fields = self._normalize(fields, meta_schema)

        # 3) Валидация по meta_schema
        self._validate(fields, meta_schema)

        # 4) Итог
        return {
            "fields": fields,
            "confidence": conf,
            "raw": raws,
            "overall_confidence": round(sum(conf.values()) / max(1, len(conf)), 3),
        }

    # --- helpers ---

    def _normalize(
        self, fields: Dict[str, Any], meta_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        specs = meta_schema.get("fields", {})
        out: Dict[str, Any] = {}
        for k, v in fields.items():
            spec = specs.get(k, {})
            t = spec.get("type")
            if v is None:
                continue
            if t == "string":
                out[k] = str(v).strip()
            elif t == "date":
                # already ISO yyyy-mm-dd в моках
                out[k] = str(v)[:10]
            elif t == "array":
                out[k] = list(v) if isinstance(v, list) else [v]
            else:
                out[k] = v
        return out

    def _validate(self, fields: Dict[str, Any], meta_schema: Dict[str, Any]) -> None:
        specs = meta_schema.get("fields", {})
        # required
        missing = [
            k for k, spec in specs.items() if spec.get("required") and k not in fields
        ]
        if missing:
            raise ValidationError(
                "DOC-005", f"Missing required fields: {', '.join(missing)}"
            )
        # regex
        for k, spec in specs.items():
            rgx = spec.get("regex")
            if rgx and k in fields:
                if not re.match(rgx, str(fields[k])):
                    raise ValidationError(
                        "DOC-005", f"Field {k} doesn't match regex {rgx}"
                    )
        # enums (simple)
        for k, spec in specs.items():
            enum_vals = spec.get("enum")
            if isinstance(enum_vals, list) and k in fields:
                if fields[k] not in enum_vals:
                    raise ValidationError("DOC-005", f"Field {k} not in enum")
