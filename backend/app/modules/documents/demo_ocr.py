from __future__ import annotations

import json
import os

from mapping_candidate import apply_mapping
from ocr_pipeline import OcrPipeline

BASE = os.path.dirname(__file__)


def run():
    pipe = OcrPipeline()

    # 1) ПАСПОРТ
    passport_schema = pipe.load_meta_schema(
        os.path.join(BASE, "meta_schemas/passport.json")
    )
    result = pipe.run(b"fake_image_bytes", "identity_document", passport_schema)
    print("Passport OCR:", json.dumps(result, ensure_ascii=False, indent=2))

    # имитация подтверждения пользователем: берём как есть
    candidate = {}
    candidate = apply_mapping(candidate, "passport", result["fields"])
    print("Candidate after passport mapping:", candidate)

    # 2) Мед. справка (template)
    med_schema = pipe.load_meta_schema(
        os.path.join(BASE, "meta_schemas/medical_cert.json")
    )
    med = pipe.run(b"fake_image_bytes", "medical_certificate", med_schema)
    print("Medical Cert OCR:", json.dumps(med, ensure_ascii=False, indent=2))

    # 3) IBAN
    bank_schema = pipe.load_meta_schema(
        os.path.join(BASE, "meta_schemas/bank_account_doc.json")
    )
    bank = pipe.run(b"fake_image_bytes", "bank_account_doc", bank_schema)
    candidate = apply_mapping(candidate, "bank_account_doc", bank["fields"])
    print("Candidate after bank mapping:", candidate)


if __name__ == "__main__":
    run()
