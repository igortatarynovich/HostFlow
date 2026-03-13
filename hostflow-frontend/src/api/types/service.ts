/**
 * Service-related types
 */

import type { UUID } from './common';

export type ServiceItemStatus = 'pending' | 'scheduled' | 'in_progress' | 'delivered' | 'cancelled';
export type ServiceOrderStatus =
  | 'draft'
  | 'quoted'
  | 'approved'
  | 'scheduled'
  | 'in_progress'
  | 'delivered'
  | 'cancelled'
  | 'refunded';

export type ServiceScheduleStatus =
  | 'reserved'
  | 'confirmed'
  | 'completed'
  | 'no_show'
  | 'cancelled';

export type ServiceUnit = 'item' | 'hour' | 'day' | 'month';

export interface AdditionalService {
  id: UUID;
  tenant_id: UUID;
  code: string;
  name: string;
  description?: string | null;
  category?: string | null;
  unit: ServiceUnit;
  base_price: number;
  estimated_cost: number;
  cost_currency: string;
  currency: string;
  vat_rate: number;
  requires_schedule: boolean;
  requires_candidate: boolean;
  result_document_type?: string | null;
  requires_documents?: string[] | null;
  sla_hours?: number | null;
  is_active: boolean;
  meta?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface AdditionalServiceAttachment {
  id: UUID;
  tenant_id: UUID;
  item_id: UUID;
  file_id: UUID;
  label?: string | null;
  created_at: string;
}

export interface AdditionalServiceSchedule {
  id: UUID;
  tenant_id: UUID;
  item_id: UUID;
  provider?: string | null;
  slot_start?: string | null;
  slot_end?: string | null;
  location?: string | null;
  status: ServiceScheduleStatus;
  meta?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface AdditionalServiceItem {
  id: UUID;
  tenant_id: UUID;
  order_id: UUID;
  service_id: UUID;
  qty: number;
  unit_price: number;
  estimated_cost: number;
  actual_cost?: number | null;
  cost_currency: string;
  cost_source?: string | null;
  cost_status: string;
  vat_rate: number;
  amount: number;
  status: ServiceItemStatus;
  required_documents?: string[] | null;
  result_document_type?: string | null;
  meta?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  service?: AdditionalService | null;
  schedules?: AdditionalServiceSchedule[];
  attachments?: AdditionalServiceAttachment[];
}

export interface AdditionalServiceOrder {
  id: UUID;
  tenant_id: UUID;
  candidate_id?: UUID | null;
  vacancy_id?: UUID | null;
  company_id?: UUID | null;
  status: ServiceOrderStatus;
  total_amount: number;
  currency: string;
  vat_total: number;
  requested_by: UUID;
  assigned_to?: UUID | null;
  notes?: string | null;
  audit?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  items: AdditionalServiceItem[];
}

export interface AdditionalServiceOrderSummary {
  order: AdditionalServiceOrder;
  blocking_items: AdditionalServiceItem[];
  missing_documents: Record<string, string[]>;
}
