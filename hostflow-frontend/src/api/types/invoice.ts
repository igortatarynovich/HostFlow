/**
 * Invoice and payment-related types
 */

export type InvoiceStatus = 'draft' | 'issued' | 'sent' | 'paid' | 'overdue' | 'cancelled' | 'refunded';
export type PaymentMethod = 'bank_transfer' | 'card' | 'cash' | 'other';
export type PaymentStatus = 'pending' | 'completed' | 'failed' | 'refunded';
export type RefundStatus = 'pending' | 'completed' | 'failed';

export interface InvoiceItem {
  id: string;
  description: string;
  quantity: number;
  unit_price: number;
  vat_rate: number;
  amount: number;
  currency: string;
}

export interface Invoice {
  id: string;
  tenant_id: string;
  company_id: string;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  total_amount: number;
  vat_total: number;
  currency: string;
  status: InvoiceStatus;
  payment_date?: string | null;
  pdf_file_id?: string | null;
  billing_details?: Record<string, any> | null;
  created_by?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  items: InvoiceItem[];
}

export interface Payment {
  id: string;
  tenant_id: string;
  invoice_id: string;
  amount: number;
  currency: string;
  payment_date: string;
  method: PaymentMethod;
  provider?: string | null;
  provider_reference?: string | null;
  reference_number?: string | null;
  status: PaymentStatus;
  created_at: string;
  updated_at: string;
}

export interface Refund {
  id: string;
  tenant_id: string;
  payment_id: string;
  amount: number;
  reason?: string | null;
  refund_date: string;
  status: RefundStatus;
  created_at: string;
  updated_at: string;
}

export interface InvoiceActivity {
  id: string;
  tenant_id: string;
  actor_id?: string | null;
  action: string;
  target_type?: string | null;
  target_id?: string | null;
  payload: Record<string, any>;
  created_at: string;
}
