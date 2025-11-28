"""
Thin shim to avoid circular imports.
Do NOT import ORM here at runtime. Use `from app.models import ...` instead.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only for hints, never executed at runtime
    from ...models import (  # type: ignore
        Document,
        DocumentType,
        DocumentTemplate,
        DocumentCheck,
        DocumentRulesetVersion,
        DocumentRulesetUsage,
        DocumentRulesetDiff,
        DocumentComplianceLog,
        DocumentMetricsDaily,
        ReportExport,
        ReportSummary,
        BulkOperation,
        BulkOperationItem,
    )
