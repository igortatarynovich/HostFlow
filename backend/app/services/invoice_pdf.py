"""
Invoice PDF generation service.
"""
from __future__ import annotations

import io
import logging
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.app.models.invoice import Invoice, InvoiceItem

logger = logging.getLogger(__name__)


def generate_invoice_pdf(invoice: Invoice) -> bytes:
    """
    Generate PDF bytes for an invoice.
    
    Args:
        invoice: Invoice model instance with items loaded
        
    Returns:
        PDF file as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=10,
    )
    story.append(Paragraph("INVOICE", title_style))
    story.append(Spacer(1, 5 * mm))
    
    # Invoice details
    details_data = [
        ['Invoice Number:', invoice.invoice_number],
        ['Issue Date:', invoice.issue_date.strftime('%Y-%m-%d') if invoice.issue_date else ''],
        ['Due Date:', invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else ''],
        ['Status:', invoice.status.upper()],
    ]
    
    details_table = Table(details_data, colWidths=[50 * mm, 100 * mm])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 10 * mm))
    
    # Billing details
    if invoice.billing_details:
        story.append(Paragraph("<b>Bill To:</b>", styles['Heading2']))
        billing_text = "<br/>".join([f"{k}: {v}" for k, v in invoice.billing_details.items() if v])
        story.append(Paragraph(billing_text, styles['Normal']))
        story.append(Spacer(1, 10 * mm))
    
    # Items table
    story.append(Paragraph("<b>Items:</b>", styles['Heading2']))
    story.append(Spacer(1, 5 * mm))
    
    items_data = [['#', 'Description', 'Qty', 'Unit Price', 'VAT %', 'Net Total', 'VAT Amount', 'Total']]
    
    for item in invoice.items:
        items_data.append([
            str(item.line_no),
            item.description,
            str(item.qty),
            f"{item.unit_price:.2f} {invoice.currency}",
            f"{item.vat_rate:.2f}%",
            f"{item.net_total:.2f} {invoice.currency}",
            f"{item.vat_amount:.2f} {invoice.currency}",
            f"{item.gross_total:.2f} {invoice.currency}",
        ])
    
    items_table = Table(items_data, colWidths=[10 * mm, 60 * mm, 15 * mm, 25 * mm, 15 * mm, 25 * mm, 25 * mm, 25 * mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e0e0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#000000')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10 * mm))
    
    # Totals
    totals_data = [
        ['Subtotal:', f"{invoice.subtotal:.2f} {invoice.currency}"],
        ['VAT Total:', f"{invoice.vat_total:.2f} {invoice.currency}"],
        ['Total Amount:', f"<b>{invoice.total_amount:.2f} {invoice.currency}</b>"],
        ['Paid Amount:', f"{invoice.paid_amount:.2f} {invoice.currency}"],
        ['Balance Due:', f"<b>{invoice.total_amount - invoice.paid_amount:.2f} {invoice.currency}</b>"],
    ]
    
    totals_table = Table(totals_data, colWidths=[50 * mm, 50 * mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(totals_table)
    
    # Notes
    if invoice.notes:
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph("<b>Notes:</b>", styles['Heading3']))
        story.append(Paragraph(invoice.notes, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.read()

