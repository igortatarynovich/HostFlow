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


def _safe_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _format_address(value: object) -> str:
    data = _safe_dict(value)
    parts = [data.get("country"), data.get("city"), data.get("street"), data.get("zip")]
    return ", ".join(str(part).strip() for part in parts if str(part or "").strip())


def _invoice_kind_label(value: object) -> str:
    kind = str(value or "").strip().lower()
    if kind == "vat":
        return "VAT Invoice"
    if kind == "proforma":
        return "Proforma Invoice"
    if kind == "correction":
        return "Correction Invoice"
    return "Invoice"


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
    billing_details = _safe_dict(invoice.billing_details)
    story.append(Paragraph(_invoice_kind_label(billing_details.get("invoice_kind")), title_style))
    story.append(Spacer(1, 5 * mm))
    
    # Invoice details
    details_data = [
        ['Type:', _invoice_kind_label(billing_details.get("invoice_kind"))],
        ['Invoice Number:', invoice.invoice_number],
        ['Issue Date:', invoice.issue_date.strftime('%Y-%m-%d') if invoice.issue_date else ''],
        ['Due Date:', invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else ''],
        ['Payment Terms:', str(_safe_dict(invoice.billing_details).get('payment_terms_days') or '')],
        ['Tax Mode:', str(_safe_dict(invoice.billing_details).get('tax_mode') or '')],
        ['Status:', invoice.status.upper()],
    ]
    correction_of = str(billing_details.get("correction_of_invoice_number") or "").strip()
    if correction_of:
        details_data.append(['Correction Of:', correction_of])
    correction_reason = str(billing_details.get("correction_reason") or "").strip()
    if correction_reason:
        details_data.append(['Correction Reason:', correction_reason])
    
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
    
    # Party and payment details
    issuer_bank = _safe_dict(billing_details.get("issuer_bank_account"))
    party_rows = []

    bill_to_lines = [
        str(billing_details.get("company_name") or "").strip(),
        f"Email: {str(billing_details.get('email') or '').strip()}",
        f"NIP: {str(billing_details.get('tax_id') or '').strip()}",
        f"Legal address: {str(billing_details.get('address') or '').strip()}",
    ]
    party_rows.append(
        [
            Paragraph("<b>Bill To</b>", styles["Heading3"]),
            Paragraph("<br/>".join([line for line in bill_to_lines if line]), styles["Normal"]),
        ]
    )

    issuer_lines = [
        str(billing_details.get("issuer_name") or "").strip(),
        f"NIP: {str(billing_details.get('issuer_tax_id') or '').strip()}",
        f"Legal address: {_format_address(billing_details.get('issuer_address'))}",
    ]
    party_rows.append(
        [
            Paragraph("<b>Issued By</b>", styles["Heading3"]),
            Paragraph("<br/>".join([line for line in issuer_lines if line]), styles["Normal"]),
        ]
    )

    if any(str(value or "").strip() for value in issuer_bank.values()):
        bank_lines = [
            f"Bank: {str(issuer_bank.get('bank_name') or '').strip()}",
            f"IBAN: {str(issuer_bank.get('iban') or '').strip()}",
            f"SWIFT/BIC: {str(issuer_bank.get('swift_bic') or '').strip()}",
            str(issuer_bank.get("label") or "").strip(),
        ]
        party_rows.append(
            [
                Paragraph("<b>Payment Details</b>", styles["Heading3"]),
                Paragraph("<br/>".join([line for line in bank_lines if line]), styles["Normal"]),
            ]
        )

    if party_rows:
        parties_table = Table(party_rows, colWidths=[45 * mm, 105 * mm])
        parties_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(parties_table)
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
