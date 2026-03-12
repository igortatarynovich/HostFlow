import type {
  DocumentKind,
  DocumentProcessType,
  DocumentRequestedFrom,
  DocumentStatus,
  DocumentWorkflow,
  DocumentFile,
} from "../types";

export type DocType = {
  id?: string;
  code: string;
  name?: string;
  description?: string | null;
  kind?: DocumentKind | string | null;
  requested_from?: DocumentRequestedFrom | string | null;
  process_type?: DocumentProcessType | string | null;
  default_expire_in_days?: number | null;
  valid_days?: number | null;
  aliases?: string[];
  required_meta?: string[];
  owner_summary_weight?: number;
  i18n_key?: string | null;
  requires_custom_name?: boolean;
  required?: boolean;
  meta_schema?: Record<string, any> | null;
  metadata_schema?: Record<string, any> | null;
  required_files?: Record<string, any> | null;
  expiry_rule?: Record<string, any> | null;
  duplicate_policy?: string | null;
  orderable?: boolean;
  title?: Record<string, any>;
};

export type PresignUpload = {
  url?: string;
  method: "POST" | "PUT";
  fields?: Record<string, string>;
  key?: string;
};

export type RulesetVersionCreateInput = {
  ruleset: Record<string, any>;
  comment?: string;
  activate?: boolean;
  origin_version_id?: string | null;
};

export type RulesetRollbackInput = {
  comment: string;
  new_comment?: string;
};

export type CreateCandidateDocumentPayload = {
  owner_id: string;
  tenant_id?: string;
  doc_type?: string;
  type_code?: string;
  kind?: DocumentKind;
  requested_from?: DocumentRequestedFrom;
  process_type?: DocumentProcessType;
  custom_name?: string | null;
  title?: string | null;
  number?: string | null;
  issue_date?: string | null;
  expire_date?: string | null;
  issued_at?: string | null;
  expires_at?: string | null;
  ordered_at?: string | null;
  valid_from?: string | null;
  reminder_days_before?: number | null;
  meta?: Record<string, any>;
  meta_json?: Record<string, any>;
  status?: DocumentStatus;
  owner_type?: string;
  company_id?: string | null;
  workflow?: Partial<DocumentWorkflow> | null;
  source?: string | null;
  external_id?: string | null;
};

export type DocumentPatchPayload = {
  doc_type?: string;
  kind?: DocumentKind;
  requested_from?: DocumentRequestedFrom;
  process_type?: DocumentProcessType;
  custom_name?: string | null;
  title?: string | null;
  number?: string | null;
  status?: DocumentStatus;
  issue_date?: string | null;
  expire_date?: string | null;
  issued_at?: string | null;
  expires_at?: string | null;
  ordered_at?: string | null;
  valid_from?: string | null;
  reminder_days_before?: number | null;
  meta?: Record<string, any>;
  meta_json?: Record<string, any>;
  workflow?: Partial<DocumentWorkflow> | null;
  owner_id?: string | null;
  owner_type?: string;
  company_id?: string | null;
  files?: Partial<DocumentFile>[] | null;
  source?: string | null;
  external_id?: string | null;
};

export type DocumentOrderInput = {
  candidate_id: string;
  doc_type: string;
  ordered_at?: string | null;
  requested_from?: string | null;
  owner_context?: Record<string, any> | null;
};

export type ListDocumentsOptions = {
  candidateId?: string;
  candidate_id?: string;
  docType?: string;
  type?: string;
  key?: string;
  kind?: DocumentKind;
  status?: DocumentStatus;
  ordered?: boolean;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
};

export type ExtractResult = {
  fields: Record<string, any>;
  confidence?: Record<string, number>;
  raw?: any;
  overall_confidence?: number;
};

export type DocumentFileDownload = {
  blob: Blob;
  filename?: string | null;
  contentType?: string | null;
};

