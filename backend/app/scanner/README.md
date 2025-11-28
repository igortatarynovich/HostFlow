# HostFlow Document Scanner Module

Comprehensive document scanning, normalization, classification, and data extraction module.

## Features

- **Universal Image Normalization Pipeline**
  - Deskew correction
  - Perspective correction
  - Border detection and cropping
  - Background removal
  - Brightness/contrast adjustment
  - Denoising
  - Adaptive binarization
  - Sharpening
  - A4 300 DPI output

- **Document Type Classification**
  - Automatic classification based on text content, MRZ, structure
  - Supports: passports, ID cards, driver licenses, residence permits, certificates, etc.

- **OCR and Data Extraction**
  - Tesseract OCR integration
  - MRZ parsing for passports/IDs
  - Field extraction (names, dates, numbers, etc.)
  - Document-specific field extraction

- **Passport Processing**
  - Processes all pages including empty ones
  - Specialized handling for multi-page passports

- **High-Quality PDF Generation**
  - A4 format at 300 DPI
  - Multi-page support
  - Professional quality output

## Usage

### Basic Usage

```python
from backend.app.scanner import DocumentScannerService
from pathlib import Path

# Initialize scanner
scanner = DocumentScannerService(target_dpi=300)

# Scan a document
result = scanner.scan_document(
    input_path=Path("/path/to/document.pdf"),
    output_dir=Path("/path/to/output"),
    doc_type_hint="passport"  # Optional
)

# Access results
print(f"Document type: {result.document_type}")
print(f"Pages: {result.pages}")
print(f"Fields: {result.fields}")
print(f"PDF path: {result.pdf_path}")
```

### JSON Output

```python
# Get JSON result
json_result = scanner.scan_to_json(
    input_path=Path("/path/to/document.pdf"),
    output_dir=Path("/path/to/output")
)

# Returns:
# {
#     "document_type": "passport",
#     "pages": 26,
#     "fields": {
#         "first_name": "JOHN",
#         "last_name": "DOE",
#         "document_number": "AB123456",
#         "expiry_date": "2025-12-31",
#         ...
#     }
# }
```

## Module Structure

- `scanner_service.py` - Main service orchestrating all components
- `preprocess.py` - Image normalization pipeline
- `classify.py` - Document type classification
- `extract_fields.py` - OCR and field extraction
- `passport_processor.py` - Specialized passport processing
- `pdf_builder.py` - PDF generation
- `document_types.py` - Document type definitions
- `validators.py` - Field validation
- `utils.py` - Utility functions

## Supported Document Types

- Passport
- Identity Document / ID Card
- Residence Permit / Karta pobytu
- Driver License / Prawo jazdy
- Qualification Card / KP
- ADR Certificate
- Tachograph Card
- Medical Certificate / Badania lekarskie
- Psychological Test / Psychotest
- Decision / Decyzja
- Visa

## Requirements

All dependencies are already in `requirements.txt`:
- opencv-python-headless
- pytesseract
- Pillow
- pdf2image
- numpy

## Testing

Run tests:
```bash
pytest backend/tests/test_scanner_module.py
```

Test on sample documents:
```python
from backend.app.scanner.test_scanner import test_scanner_on_samples

test_scanner_on_samples()
```

## Configuration

The scanner uses Tesseract OCR. Ensure Tesseract is installed:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-pol tesseract-ocr-rus tesseract-ocr-ukr

# macOS
brew install tesseract tesseract-lang
```

OCR languages can be configured via environment variables (see `extract_fields.py`).

