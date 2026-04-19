/**
 * Document-related types
 */

import type { UUID } from './common';

export type DocumentStatus =
  | 'missing'
  | 'requested'
  | 'in_progress'
  | 'received'
  | 'approved'
  | 'rejected'
  | 'expired';

export type DocumentKind = 'driver' | 'employer' | 'process';
export type DocumentRequestedFrom = 'driver' | 'employer' | 'agency';
export type DocumentProcessType =
  | 'none'
  | 'work_permit'
  | 'visa'
  | 'residence_card'
  | 'residence_permit'
  | 'tachograph_card'
  | 'driver_license_exchange'
  | 'driver_license'
  | 'eu_driver_license'
  | 'adr'
  | 'code95'
  | 'qualification_code95'
  | 'driver_certificate'
  | 'decision'
  | 'swiadectwo_kierowcy'
  | 'other';

export type DocumentWorkflowStepStatus =
  | 'pending'
  | 'in_progress'
  | 'done'
  | 'blocked'
  | 'waiting'
  | 'paused'
  | 'skipped'
  | (string & {});

export interface DocumentFile {
  name: string;
  url?: string | null;
  size?: number | null;
  mime?: string | null;
  uploaded_at?: string | null;
  uploaded_by?: string | null;
  version?: number | null;
}

export interface DocumentReminder {
  due_at: string;
  message: string;
  offset_days: number;
  status: string;
  kind: 'expiry' | 'workflow_step' | (string & {});
  step_code?: string | null;
}

export interface DocumentCheck {
  id: string;
  document_id: string;
  reviewer_id: string | null;
  decision: 'approved' | 'rejected';
  reason_code?: string | null;
  comment?: string | null;
  payload?: Record<string, any> | null;
  created_at: string;
}

export interface DocumentWorkflowStep {
  code: string;
  title: string;
  description?: string | null;
  status: DocumentWorkflowStepStatus;
  started_at?: string | null;
  completed_at?: string | null;
  assigned_to?: string | null;
  notes?: string | null;
  depends_on?: string[] | null;
  blocking?: boolean;
  meta?: Record<string, any> | null;
}

export interface DocumentWorkflow {
  process_type?: DocumentProcessType | null;
  current_step?: string | null;
  steps?: DocumentWorkflowStep[];
  started_at?: string | null;
  completed_at?: string | null;
  meta?: Record<string, any> | null;
}

export type DocumentReadinessState =
  | 'pending'
  | 'requested'
  | 'ordered'
  | 'in_progress'
  | 'awaiting_review'
  | 'ready'
  | 'problem'
  | (string & {});

export interface Document {
  id: UUID;
  tenant_id: UUID;
  owner_id: UUID;
  owner_type?: string | null;
  doc_type?: string | null;
  type_code?: string | null;
  kind?: DocumentKind | null;
  requested_from?: DocumentRequestedFrom | null;
  process_type?: DocumentProcessType | null;
  custom_name?: string | null;
  title?: string | null;
  number?: string | null;
  status?: DocumentStatus | null;
  issue_date?: string | null;
  expire_date?: string | null;
  issued_at?: string | null;
  expires_at?: string | null;
  ordered_at?: string | null;
  valid_from?: string | null;
  reminder_days_before?: number | null;
  meta?: Record<string, any> | null;
  meta_json?: Record<string, any> | null;
  files?: DocumentFile[] | null;
  has_files?: boolean | null;
  reminders?: DocumentReminder[] | null;
  workflow?: DocumentWorkflow | null;
  last_check?: DocumentCheck | null;
  readiness_state?: DocumentReadinessState | null;
  company_id?: UUID | null;
  source?: string | null;
  external_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface DocumentSummaryRequired {
  doc_type: string;
  required: boolean;
  has_files: boolean;
  status?: DocumentStatus | null;
  expire_date?: string | null;
}

export interface DocumentSummary {
  total: number;
  ready: number;
  missing: number;
  expiring_soon: number;
  expired: number;
  required: DocumentSummaryRequired[];
  checklist?: CandidateDocumentChecklist | null;
}

export interface CandidateDocumentsSummaryResponse {
  candidate_id: UUID;
  summary: DocumentSummary;
}

export interface CandidateDocumentChecklist {
  requiredTypes?: string[];
  optionalTypes?: string[];
  missingTypes?: string[];
  readyTypes?: string[];
}

