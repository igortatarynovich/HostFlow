"""Document Runtime Engine — instance lifecycle evaluation."""

from backend.app.document_runtime.constants import DOCUMENT_RUNTIME_V1
from backend.app.document_runtime.evaluator import evaluate_document_runtime

__all__ = ["DOCUMENT_RUNTIME_V1", "evaluate_document_runtime"]
