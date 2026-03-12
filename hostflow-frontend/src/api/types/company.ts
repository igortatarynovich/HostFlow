/**
 * Company and vacancy-related types
 */

import type { UUID } from './common';

/** Компания */
export interface Company {
  id: UUID;
  name: string;
  legal_name?: string | null;
  reg_no?: string | null;
  tax_id?: string | null;
  vat_eu?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  notes?: string | null;
  is_archived?: boolean | null;
  country_code?: string | null;
  country?: string | null;
  city?: string | null;
  address?: string | null;
  contacts?: Record<string, unknown> | null;
  extra?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CompanyReadiness {
  company_id: UUID;
  has_legal: boolean;
  has_primary_contact: boolean;
  has_primary_bank: boolean;
  fin_check_status: string;
  billing_ready: boolean;
  compliance_valid: boolean;
  client_portal_enabled: boolean;
  readiness_score?: number | null;
  readiness_state?: string | null;
}

/** Вакансия */
export interface Vacancy {
  id: UUID;
  company_id: UUID;
  title: string;
  status: string;
  description?: string | null;
  location?: string | null;
  company_name?: string | null;
  currency?: string | null;
  is_open?: boolean | null;
  is_active?: boolean | null;
  is_archived?: boolean | null;
}

/** Запись доступа к компании (UI-friendly + backward-compatible) */
export interface CompanyAccessEntry {
  // поля, которые читает админский UI
  id: string;
  email: string;
  role: string; // 'viewer' | 'editor' | 'admin' | ...
  can_edit: boolean;
  created_at?: string;

  // легаси/низкоуровневые поля сохраним как опциональные,
  // чтобы не ломать старые вызовы API, если где-то используются
  user_id?: string;
  company_id?: string;
  access_level?: string;
  granted_at?: string;
  revoked_at?: string | null;
}

