"""
OCR and field extraction from documents.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

import pytesseract

logger = logging.getLogger(__name__)


class FieldExtractor:
    """Extract structured fields from document text using OCR."""
    
    def __init__(self):
        # Common patterns
        self.date_patterns = [
            re.compile(r'(\d{4})[./-](\d{2})[./-](\d{2})'),  # YYYY-MM-DD
            re.compile(r'(\d{2})[./-](\d{2})[./-](\d{4})'),  # DD-MM-YYYY
        ]
        self.pesel_pattern = re.compile(r'\b\d{11}\b')  # PESEL: 11 digits
        self.passport_pattern = re.compile(r'\b[A-Z]{1,3}\d{6,9}\b')  # Passport number
        self.mrz_pattern = re.compile(
            r'([A-Z0-9<]{30,})[\n\r]+([A-Z0-9<]{30,})',  # MRZ lines
            re.MULTILINE
        )
    
    def extract(self, image, doc_type: str, ocr_text: Optional[str] = None) -> Dict[str, str]:
        """
        Extract fields from document.
        
        Args:
            image: Preprocessed image
            doc_type: Document type
            ocr_text: Optional pre-extracted OCR text
            
        Returns:
            Dictionary of extracted fields
        """
        fields: Dict[str, str] = {}
        
        # Extract OCR text if not provided
        if ocr_text is None:
            try:
                # Use appropriate language based on document type
                lang = self._get_ocr_language(doc_type)
                ocr_text = pytesseract.image_to_string(image, lang=lang)
            except Exception as e:
                logger.warning(f"OCR extraction failed: {e}")
                ocr_text = ""
        
        if not ocr_text.strip():
            return fields
        
        # Extract MRZ if present
        mrz = self._extract_mrz(ocr_text)
        if mrz:
            fields["mrz"] = mrz
            # Parse MRZ for passport/ID fields
            if doc_type == "passport":
                mrz_fields = self._parse_passport_mrz(mrz)
                fields.update(mrz_fields)
        
        # Extract common fields
        fields.update(self._extract_dates(ocr_text))
        fields.update(self._extract_numbers(ocr_text, doc_type))
        fields.update(self._extract_names(ocr_text))
        
        # Document-specific extraction
        if doc_type == "passport":
            fields.update(self._extract_passport_fields(ocr_text))
        elif doc_type == "driver_license":
            fields.update(self._extract_driver_license_fields(ocr_text))
        elif doc_type == "residence_permit":
            fields.update(self._extract_residence_permit_fields(ocr_text))
        elif doc_type in ("medical_certificate", "psychological_test"):
            fields.update(self._extract_certificate_fields(ocr_text))
        
        return fields
    
    def _get_ocr_language(self, doc_type: str) -> str:
        """Get OCR language configuration based on document type."""
        # Polish documents
        if doc_type in ("residence_permit", "driver_license", "qualification_card",
                       "medical_certificate", "psychological_test", "decision"):
            return "pol+eng"
        # Passports can be in various languages
        if doc_type == "passport":
            return "eng+pol+rus+ukr"
        # Default: English + Polish
        return "eng+pol"
    
    def _extract_mrz(self, text: str) -> Optional[str]:
        """Extract MRZ from text."""
        match = self.mrz_pattern.search(text)
        if match:
            return "\n".join(match.groups())
        return None
    
    def _parse_passport_mrz(self, mrz: str) -> Dict[str, str]:
        """Parse passport MRZ to extract fields."""
        fields: Dict[str, str] = {}
        lines = mrz.strip().split('\n')
        
        if len(lines) >= 2:
            # First line: document type, country, name
            line1 = lines[0]
            if line1.startswith('P<'):
                # Passport MRZ format
                # Extract country code (positions 2-4)
                if len(line1) > 4:
                    fields["issuing_country"] = line1[2:5]
                
                # Extract name (after country code, before <<)
                name_part = line1[5:].split('<<')
                if len(name_part) >= 2:
                    surname = name_part[0].replace('<', ' ').strip()
                    given_names = name_part[1].replace('<', ' ').strip() if len(name_part) > 1 else ""
                    if surname:
                        fields["last_name"] = surname
                    if given_names:
                        fields["first_name"] = given_names
            
            # Second line: document number, dates, etc.
            if len(lines) > 1 and len(lines[1]) >= 36:
                line2 = lines[1]
                # Document number (first 9 chars, remove <)
                doc_num = line2[:9].replace('<', '').strip()
                if doc_num:
                    fields["document_number"] = doc_num
                
                # Date of birth (positions 13-18, YYMMDD)
                if len(line2) >= 19:
                    dob_str = line2[13:19]
                    dob = self._parse_mrz_date(dob_str)
                    if dob:
                        fields["date_of_birth"] = dob
                
                # Sex (position 20)
                if len(line2) >= 21:
                    sex = line2[20]
                    if sex in ('M', 'F'):
                        fields["sex"] = sex
                
                # Expiry date (positions 21-26, YYMMDD)
                if len(line2) >= 27:
                    exp_str = line2[21:27]
                    exp = self._parse_mrz_date(exp_str)
                    if exp:
                        fields["expiry_date"] = exp
        
        return fields
    
    def _parse_mrz_date(self, date_str: str) -> Optional[str]:
        """Parse MRZ date format (YYMMDD) to ISO format."""
        if len(date_str) != 6 or not date_str.isdigit():
            return None
        
        try:
            yy = int(date_str[:2])
            mm = int(date_str[2:4])
            dd = int(date_str[4:6])
            
            # Assume 20xx for years 00-50, 19xx for 51-99
            year = 2000 + yy if yy <= 50 else 1900 + yy
            
            # Validate date
            if 1 <= mm <= 12 and 1 <= dd <= 31:
                return f"{year:04d}-{mm:02d}-{dd:02d}"
        except (ValueError, IndexError):
            pass
        
        return None
    
    def _extract_dates(self, text: str) -> Dict[str, str]:
        """Extract dates from text."""
        dates: Dict[str, str] = {}
        found_dates = []
        
        for pattern in self.date_patterns:
            for match in pattern.finditer(text):
                try:
                    if len(match.groups()) == 3:
                        if len(match.group(1)) == 4:  # YYYY-MM-DD
                            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        else:  # DD-MM-YYYY
                            day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        
                        # Validate date
                        if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                            date_str = f"{year:04d}-{month:02d}-{day:02d}"
                            found_dates.append(date_str)
                except (ValueError, IndexError):
                    continue
        
        # Assign dates to common field names
        if found_dates:
            # First date might be issue date
            dates["issue_date"] = found_dates[0]
            if len(found_dates) > 1:
                # Last date might be expiry date
                dates["expiry_date"] = found_dates[-1]
        
        return dates
    
    def _extract_numbers(self, text: str, doc_type: str) -> Dict[str, str]:
        """Extract document numbers and identifiers."""
        numbers: Dict[str, str] = {}
        
        # PESEL
        pesel_match = self.pesel_pattern.search(text)
        if pesel_match:
            numbers["pesel"] = pesel_match.group(0)
        
        # Passport number
        if doc_type == "passport":
            passport_match = self.passport_pattern.search(text.upper())
            if passport_match:
                numbers["document_number"] = passport_match.group(0)
        
        return numbers
    
    def _extract_names(self, text: str) -> Dict[str, str]:
        """Extract names from text (basic heuristic)."""
        names: Dict[str, str] = {}
        
        # Look for patterns like "Name:", "Surname:", etc.
        name_patterns = [
            (re.compile(r'(?:name|imie|имя)[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', re.I), "first_name"),
            (re.compile(r'(?:surname|nazwisko|фамилия)[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', re.I), "last_name"),
        ]
        
        for pattern, field_name in name_patterns:
            match = pattern.search(text)
            if match:
                names[field_name] = match.group(1).strip()
        
        return names
    
    def _extract_passport_fields(self, text: str) -> Dict[str, str]:
        """Extract passport-specific fields."""
        fields: Dict[str, str] = {}
        
        # Nationality
        nationality_match = re.search(r'(?:nationality|narodowość|гражданство)[\s:]+([A-Z]{2,3})', text, re.I)
        if nationality_match:
            fields["nationality"] = nationality_match.group(1).upper()
        
        return fields
    
    def _extract_driver_license_fields(self, text: str) -> Dict[str, str]:
        """Extract driver license-specific fields."""
        fields: Dict[str, str] = {}
        
        # Categories (e.g., B, C, CE)
        category_match = re.search(r'(?:cat|kategoria|category)[\s.:]+([A-Z]+(?:\s+[A-Z]+)*)', text, re.I)
        if category_match:
            fields["categories"] = category_match.group(1).upper()
        
        return fields
    
    def _extract_residence_permit_fields(self, text: str) -> Dict[str, str]:
        """Extract residence permit-specific fields."""
        fields: Dict[str, str] = {}
        
        # Permit number
        permit_match = re.search(r'(?:nr|number|numer)[\s:]+([A-Z0-9/-]+)', text, re.I)
        if permit_match:
            fields["document_number"] = permit_match.group(1).strip()
        
        return fields
    
    def _extract_certificate_fields(self, text: str) -> Dict[str, str]:
        """Extract certificate-specific fields (medical, psychological)."""
        fields: Dict[str, str] = {}
        
        # Next examination date
        next_exam_match = re.search(
            r'(?:next|następne|следующее)[\s:]+(?:examination|badanie|обследование)[\s:]+(\d{4}[./-]\d{2}[./-]\d{2})',
            text, re.I
        )
        if next_exam_match:
            fields["next_examination_date"] = next_exam_match.group(1)
        
        return fields

