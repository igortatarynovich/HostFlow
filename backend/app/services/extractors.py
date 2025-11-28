from __future__ import annotations

import mimetypes
import os
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Union

# --- Конфиг через env ---
OCR_LANGS = os.getenv("OCR_LANGS", "eng+rus+ukr+pol")
OCR_ENABLE = os.getenv("OCR_ENABLE", "1") not in ("0", "false", "False")
PDF_OCR_PAGE_LIMIT = int(os.getenv("PDF_OCR_PAGE_LIMIT", "10"))
MIN_TEXT_LEN_FOR_SKIP_OCR = int(os.getenv("MIN_TEXT_LEN_FOR_SKIP_OCR", "50"))

# Человеческие названия (при желании можно использовать)
HUMAN_TITLES: Dict[str, str] = {
    "passport": "Паспорт",
    "driver_license": "Водительское удостоверение",
    "residence_card": "Karta pobytu",
    "work_permit": "Świadectwo kwalifikacji / Разрешение на работу",
    "visa": "Виза",
    "document": "Документ",
}

KEYWORDS = [
    ("passport", ("паспорт", "passport", "паспорт гражданина", "паспорт громадянина")),
    (
        "driver_license",
        ("водительск", "prawo jazdy", "driver", "licence", "license", "права"),
    ),
    (
        "residence_card",
        ("karta pobytu", "карта побыту", "вид на жительство", "residence card"),
    ),
    (
        "work_permit",
        ("świadectwo kwalifik", "zezwolenie na pracę", "разрешение на работу"),
    ),
    ("visa", ("виза", "visa")),
]

DATE_PATTERNS = [
    r"(\d{4})[./-](\d{2})[./-](\d{2})",
    r"(\d{2})[./-](\d{2})[./-](\d{4})",
]
NUMBER_RE = re.compile(r"\b([A-Z]{1,3}\d{5,}|[A-Z0-9]{6,})\b", re.I)

# --- HEIC/HEIF поддержка для Pillow ---
try:
    from pillow_heif import register_heif_opener  # type: ignore

    register_heif_opener()
except Exception:
    pass


@dataclass
class Extracted:
    text: str
    used_ocr: bool


# ---------------- ВСПОМОГАТЕЛЬНОЕ ----------------
def _to_date(yyyy: int, mm: int, dd: int) -> Optional[date]:
    try:
        return date(yyyy, mm, dd)
    except ValueError:
        return None


def _find_any_date(t: str) -> Optional[date]:
    for p in DATE_PATTERNS:
        m = re.search(p, t)
        if not m:
            continue
        g = m.groups()
        try:
            if len(g[0]) == 4:  # YYYY MM DD
                return _to_date(int(g[0]), int(g[1]), int(g[2]))
            else:  # DD MM YYYY
                return _to_date(int(g[2]), int(g[1]), int(g[0]))
        except Exception:
            continue
    return None


def _find_labeled_date(t: str, labels: Tuple[str, ...]) -> Optional[date]:
    tl = t.lower()
    nearby = 150
    for label in labels:
        i = tl.find(label)
        if i == -1:
            continue
        seg = t[max(0, i - nearby) : i + nearby]
        d = _find_any_date(seg)
        if d:
            return d
    return None


def _find_number(t: str) -> Optional[str]:
    m = NUMBER_RE.search(t)
    return m.group(1) if m else None


def _by_keywords(hay: str) -> Optional[str]:
    low = hay.lower()
    for key, words in KEYWORDS:
        if any(w in low for w in words):
            return key
    return None


def _guess_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or ""


# -------------- ИЗВЛЕЧЕНИЕ ТЕКСТА --------------
def _extract_text_txt_like(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _extract_text_docx(path: str) -> str:
    try:
        from docx import Document as Docx  # python-docx

        doc = Docx(path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""


def _extract_text_pdf_layer(path: str) -> str:
    # 1) pypdf
    try:
        from pypdf import PdfReader

        reader = PdfReader(path)
        buf: List[str] = []
        for page in reader.pages:
            try:
                txt = page.extract_text() or ""
                if txt:
                    buf.append(txt)
            except Exception:
                continue
        text = "\n".join(buf).strip()
        if text:
            return text
    except Exception:
        pass

    # 2) pdfminer.six
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract_text

        text = pdfminer_extract_text(path) or ""
        return text.strip()
    except Exception:
        return ""


def _ocr_image_pil(image: Any) -> str:
    if not OCR_ENABLE:
        return ""
    try:
        import pytesseract

        return pytesseract.image_to_string(image, lang=OCR_LANGS) or ""
    except Exception:
        return ""


def _ocr_image_path(path: str) -> str:
    if not OCR_ENABLE:
        return ""
    try:
        from PIL import Image, ImageOps, ImageFile

        img: Union[Image.Image, ImageFile.ImageFile] = Image.open(path)
        img = ImageOps.autocontrast(ImageOps.grayscale(img))
        return _ocr_image_pil(img)
    except Exception:
        return ""


def _ocr_pdf(path: str, page_limit: int) -> str:
    if not OCR_ENABLE:
        return ""
    try:
        from pdf2image import convert_from_path

        pages = convert_from_path(path, dpi=250)
        buf: List[str] = []
        for idx, page in enumerate(pages):
            if idx >= page_limit:
                break
            buf.append(_ocr_image_pil(page))
        return "\n".join(buf).strip()
    except Exception:
        return ""


def extract_text(path: str) -> Extracted:
    """
    Главная точка входа. Возвращает Extracted(text, used_ocr).
    """
    name = os.path.basename(path).lower()

    # txt-like
    if name.endswith((".txt", ".csv", ".log", ".json", ".md")):
        return Extracted(_extract_text_txt_like(path), False)

    # docx
    if name.endswith(".docx"):
        t = _extract_text_docx(path)
        return Extracted(t, False)

    mime = _guess_mime(path)

    # изображения (включая HEIC/HEIF)
    if name.endswith(
        (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic", ".heif")
    ) or mime.startswith("image/"):
        t = _ocr_image_path(path)
        return Extracted(t, True)

    # pdf
    if name.endswith(".pdf") or mime == "application/pdf":
        text_layer = _extract_text_pdf_layer(path)
        if len(text_layer) >= MIN_TEXT_LEN_FOR_SKIP_OCR:
            return Extracted(text_layer, False)
        ocr_text = _ocr_pdf(path, PDF_OCR_PAGE_LIMIT)
        if len(ocr_text) > len(text_layer):
            return Extracted(ocr_text, True)
        return Extracted(text_layer, False)

    return Extracted("", False)


# -------------- КЛАССИФИКАЦИЯ + ПОЛЯ --------------
def classify_text(t: str, filename: Optional[str] = None) -> Dict[str, Optional[str]]:
    key = _by_keywords(t) or _by_keywords(filename or "") or "document"
    return {"key": key}


def auto_fill_from_file(
    path: str, hinted_key: Optional[str] = None
) -> Dict[str, Optional[str]]:
    ext = extract_text(path)
    info = classify_text(ext.text, filename=os.path.basename(path)) or {}
    key = (hinted_key or info.get("key") or "document").strip()

    issued = _find_labeled_date(
        ext.text,
        (
            "issued",
            "issue",
            "date of issue",
            "дата выдачи",
            "wydano",
            "wydany",
            "data wydania",
        ),
    )
    expires = _find_labeled_date(
        ext.text,
        (
            "expires",
            "expiry",
            "valid to",
            "valid until",
            "действует до",
            "срок действия до",
            "ważny do",
            "ważna do",
            "ważne do",
        ),
    )

    if not issued:
        issued = _find_any_date(ext.text)
    if not expires:
        for patt in DATE_PATTERNS:
            it = list(re.finditer(patt, ext.text))
            if it:
                s = it[-1].group(0)
                expires = _find_any_date(s)
                break

    number = _find_number(ext.text)

    def fmt(d: Optional[date]) -> Optional[str]:
        return d.strftime("%Y-%m-%d") if d else None

    return {
        "key": key,
        "number": number,
        "issued_at": fmt(issued),
        "expires_at": fmt(expires),
    }
