"""
Test script for Document Scanner module.
Run this to test the scanner on sample documents.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .scanner_service import DocumentScannerService


def test_scanner_on_samples():
    """Test scanner on sample documents."""
    samples_dir = Path("/opt/HostFlow/samples")
    if not samples_dir.exists():
        print(f"Samples directory not found: {samples_dir}")
        return
    
    scanner = DocumentScannerService()
    
    # Find all PDF and image files
    test_files = []
    for ext in ["*.pdf", "*.jpg", "*.jpeg", "*.png"]:
        test_files.extend(samples_dir.rglob(ext))
    
    if not test_files:
        print("No test files found in samples directory")
        return
    
    print(f"Found {len(test_files)} test files\n")
    
    results = []
    
    for test_file in test_files[:10]:  # Limit to first 10 files
        print(f"Processing: {test_file.name}")
        print(f"  Path: {test_file}")
        
        try:
            # Create output directory
            output_dir = test_file.parent / "scanner_output" / test_file.stem
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Scan document
            result = scanner.scan_document(test_file, output_dir)
            
            # Print results
            print(f"  Type: {result.document_type}")
            print(f"  Pages: {result.pages}")
            print(f"  Fields: {len(result.fields)}")
            if result.fields:
                for key, value in list(result.fields.items())[:5]:
                    print(f"    {key}: {value}")
            if result.pdf_path:
                print(f"  PDF: {result.pdf_path}")
            print()
            
            results.append({
                "file": str(test_file),
                "type": result.document_type,
                "pages": result.pages,
                "fields": result.fields,
            })
            
        except Exception as e:
            print(f"  ERROR: {e}\n")
            results.append({
                "file": str(test_file),
                "error": str(e),
            })
    
    # Save results
    results_file = samples_dir / "scanner_test_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {results_file}")
    print(f"Processed {len(results)} files")


if __name__ == "__main__":
    test_scanner_on_samples()

