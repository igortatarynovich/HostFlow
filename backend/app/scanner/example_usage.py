"""
Example usage of Document Scanner module.
"""

from pathlib import Path

from backend.app.scanner import DocumentScannerService


def example_scan_single_document():
    """Example: Scan a single document."""
    scanner = DocumentScannerService()
    
    # Scan document
    result = scanner.scan_document(
        input_path=Path("/opt/HostFlow/samples/SITHOLE/Passport.pdf"),
        output_dir=Path("/tmp/scanner_output"),
    )
    
    print(f"Document Type: {result.document_type}")
    print(f"Pages: {result.pages}")
    print(f"Fields Extracted: {len(result.fields)}")
    for key, value in result.fields.items():
        print(f"  {key}: {value}")
    
    if result.pdf_path:
        print(f"\nProcessed PDF saved to: {result.pdf_path}")


def example_scan_multiple_documents():
    """Example: Scan multiple documents from samples directory."""
    scanner = DocumentScannerService()
    samples_dir = Path("/opt/HostFlow/samples")
    
    # Find all PDFs
    pdf_files = list(samples_dir.rglob("*.pdf"))
    
    for pdf_file in pdf_files[:5]:  # Process first 5
        print(f"\nProcessing: {pdf_file.name}")
        
        try:
            result = scanner.scan_to_json(
                input_path=pdf_file,
                output_dir=pdf_file.parent / "scanner_output",
            )
            
            print(f"  Type: {result['document_type']}")
            print(f"  Pages: {result['pages']}")
            print(f"  Fields: {len(result['fields'])}")
            
        except Exception as e:
            print(f"  Error: {e}")


def example_passport_processing():
    """Example: Process a passport (all pages)."""
    scanner = DocumentScannerService()
    
    result = scanner.scan_document(
        input_path=Path("/opt/HostFlow/samples/SITHOLE/Passport.pdf"),
        output_dir=Path("/tmp/passport_output"),
        doc_type_hint="passport",
    )
    
    print(f"Passport processed: {result.pages} pages")
    print(f"Extracted fields:")
    for key, value in result.fields.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    print("Example 1: Scan single document")
    print("-" * 50)
    try:
        example_scan_single_document()
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n\nExample 2: Scan multiple documents")
    print("-" * 50)
    try:
        example_scan_multiple_documents()
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n\nExample 3: Process passport")
    print("-" * 50)
    try:
        example_passport_processing()
    except Exception as e:
        print(f"Error: {e}")

