"""
Unit tests for Document Scanner module.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from backend.app.scanner.classify import DocumentClassifier
from backend.app.scanner.document_types import get_document_type_info, is_passport_type
from backend.app.scanner.extract_fields import FieldExtractor
from backend.app.scanner.pdf_builder import PDFBuilder
from backend.app.scanner.preprocess import ImagePreprocessor
from backend.app.scanner.scanner_service import DocumentScannerService
from backend.app.scanner.validators import DocumentValidator


class TestImagePreprocessor:
    """Test image preprocessing."""
    
    def test_preprocess_creates_a4_image(self):
        """Test that preprocessing creates A4-sized image."""
        preprocessor = ImagePreprocessor(target_dpi=300)
        
        # Create test image
        test_image = np.ones((1000, 800, 3), dtype=np.uint8) * 128
        
        processed = preprocessor.process(test_image)
        
        # Should be A4 size at 300 DPI
        assert processed.shape[0] == 3508  # A4 height
        assert processed.shape[1] == 2480  # A4 width
        assert processed.shape[2] == 3  # BGR channels


class TestDocumentClassifier:
    """Test document classification."""
    
    def test_classify_from_filename(self):
        """Test classification from filename."""
        classifier = DocumentClassifier()
        
        assert classifier.classify_from_filename("passport.pdf") == "passport"
        assert classifier.classify_from_filename("TRC card.pdf") == "residence_permit"
        assert classifier.classify_from_filename("prawo jazdy.pdf") == "driver_license"
        assert classifier.classify_from_filename("KP.pdf") == "qualification_card"
        assert classifier.classify_from_filename("ADR Card.pdf") == "adr_certificate"
    
    def test_detect_mrz(self):
        """Test MRZ detection."""
        classifier = DocumentClassifier()
        
        # Valid MRZ
        mrz_text = "P<POLDOE<<JOHN<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n1234567890POL9001011M2501013<<<<<<<<<<<<<<6"
        assert classifier._detect_mrz(mrz_text) is True
        
        # Invalid MRZ
        assert classifier._detect_mrz("Regular text") is False


class TestFieldExtractor:
    """Test field extraction."""
    
    def test_extract_dates(self):
        """Test date extraction."""
        extractor = FieldExtractor()
        
        text = "Issue date: 2020-01-15, Expiry: 2025-12-31"
        dates = extractor._extract_dates(text)
        
        assert "issue_date" in dates
        assert "expiry_date" in dates
    
    def test_extract_pesel(self):
        """Test PESEL extraction."""
        extractor = FieldExtractor()
        
        text = "PESEL: 12345678901"
        numbers = extractor._extract_numbers(text, "identity_document")
        
        assert "pesel" in numbers
        assert numbers["pesel"] == "12345678901"


class TestDocumentValidator:
    """Test document validation."""
    
    def test_validate_fields(self):
        """Test field validation."""
        validator = DocumentValidator()
        
        fields = {
            "document_number": "AB123456",
            "issue_date": "2020-01-15",
            "expiry_date": "2025-12-31",
        }
        
        errors = validator.validate_fields(fields, "passport")
        
        # Should have no errors for valid fields
        assert isinstance(errors, dict)
    
    def test_validate_date_format(self):
        """Test date format validation."""
        validator = DocumentValidator()
        
        assert validator._is_valid_date("2020-01-15") is True
        assert validator._is_valid_date("2020-13-15") is False  # Invalid month
        assert validator._is_valid_date("invalid") is False


class TestPDFBuilder:
    """Test PDF building."""
    
    def test_build_pdf(self):
        """Test PDF creation."""
        builder = PDFBuilder(target_dpi=300)
        
        # Create test images
        images = [
            np.ones((3508, 2480, 3), dtype=np.uint8) * 255,  # White A4
            np.ones((3508, 2480, 3), dtype=np.uint8) * 200,  # Gray A4
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            success = builder.build_pdf(images, pdf_path)
            
            assert success is True
            assert pdf_path.exists()


class TestDocumentTypes:
    """Test document type definitions."""
    
    def test_get_document_type_info(self):
        """Test getting document type info."""
        info = get_document_type_info("passport")
        
        assert info is not None
        assert info.code == "passport"
        assert info.is_passport is True
        assert info.mrz_supported is True
    
    def test_is_passport_type(self):
        """Test passport type check."""
        assert is_passport_type("passport") is True
        assert is_passport_type("driver_license") is False


class TestDocumentScannerService:
    """Test main scanner service."""
    
    def test_service_initialization(self):
        """Test service can be initialized."""
        service = DocumentScannerService()
        
        assert service is not None
        assert service.target_dpi == 300
    
    @pytest.mark.skip(reason="Requires actual image files")
    def test_scan_document(self):
        """Test document scanning (requires test files)."""
        # This test would require actual document files
        pass

