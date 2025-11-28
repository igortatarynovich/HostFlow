"""
Test scanner on real document samples from /opt/HostFlow/samples
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import cv2
from backend.app.scanner.preprocess import ImagePreprocessor
from backend.app.scanner.classify import DocumentClassifier
from backend.app.scanner.scanner_service import DocumentScannerService

def test_on_samples():
    """Test scanner on real document samples."""
    samples_dir = Path("/opt/HostFlow/samples")
    
    # Find sample images
    sample_files = []
    for ext in ["*.pdf", "*.jpg", "*.jpeg", "*.png"]:
        sample_files.extend(list(samples_dir.rglob(ext)))
    
    print(f"Found {len(sample_files)} sample files")
    
    preprocessor = ImagePreprocessor(target_dpi=300)
    classifier = DocumentClassifier()
    scanner = DocumentScannerService(target_dpi=300)
    
    for sample_file in sample_files[:5]:  # Test first 5
        print(f"\n{'='*60}")
        print(f"Testing: {sample_file.name}")
        print(f"Path: {sample_file}")
        
        try:
            # Load image
            if sample_file.suffix.lower() == ".pdf":
                from backend.app.scanner.utils import pdf_to_images
                images = pdf_to_images(sample_file)
                if not images:
                    print("  ❌ Failed to load PDF")
                    continue
                image = images[0]
            else:
                image = cv2.imread(str(sample_file))
                if image is None:
                    print("  ❌ Failed to load image")
                    continue
            
            print(f"  ✓ Loaded image: {image.shape}")
            
            # Test preprocessing
            try:
                processed = preprocessor.process(image)
                print(f"  ✓ Preprocessed: {processed.shape}")
            except Exception as e:
                print(f"  ❌ Preprocessing failed: {e}")
                import traceback
                traceback.print_exc()
                continue
            
            # Test classification
            try:
                doc_type, confidence = classifier.classify(processed)
                print(f"  ✓ Classified as: {doc_type} (confidence: {confidence:.2f})")
            except Exception as e:
                print(f"  ❌ Classification failed: {e}")
            
            # Test full scan
            try:
                result = scanner.scan_document(sample_file, output_dir=None)
                print(f"  ✓ Full scan: {result.document_type}, {len(result.fields)} fields")
            except Exception as e:
                print(f"  ❌ Full scan failed: {e}")
                import traceback
                traceback.print_exc()
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_on_samples()

