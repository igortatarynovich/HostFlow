"""Sales intake destination handlers."""

from backend.app.modules.sales.intake.inquiry_draft_handler import (
    HANDLER_ID,
    handle_sales_inquiry_draft,
)

__all__ = ["HANDLER_ID", "handle_sales_inquiry_draft"]
