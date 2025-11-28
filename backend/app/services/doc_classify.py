from __future__ import annotations

import re
from typing import Dict, Optional

# backend/app/services/doc_classify.py



def extract_text(path: str) -> str:
    # Заглушка: для PDF/изображений сюда можно подключить pdfplumber/pytesseract.
    # Сейчас просто читаем как текст (для демо / теста).
    try:
        with open(path, "rb") as f:
            data = f.read()
        return data.decode(errors="ignore")
    except Exception:
        return ""


def classify_text(text: str) -> Optional[Dict]:
    t = text.lower()
    # очень простые эвристики
    if "passport" in t or "rzeczpospolita" in t or "p<" in t:
        # MRZ эвристика
        mrz_ok = bool(re.search(r"\bp<", t))
        return {"key": "passport", "confidence": 0.8, "mrz_ok": mrz_ok}
    if "prawo jazdy" in t or "driver" in t:
        return {"key": "driver_license", "confidence": 0.7}
    if "kod 95" in t or "code 95" in t or "kwalifikacja" in t:
        return {"key": "code95", "confidence": 0.7}
    return None
