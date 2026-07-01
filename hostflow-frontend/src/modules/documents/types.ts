/**
 * Types for document management module
 */

import type { DocumentKind, DocumentStatus, DocumentRequestedFrom, DocumentProcessType } from "../../api/types";

export type DocType = {
  id?: string;
  code: string;
  name?: string;
  required?: boolean;
  meta_schema?: any;
  metadata_schema?: Record<string, any> | null;
  required_files?: Record<string, any> | null;
  orderable?: boolean | null;
  // Catalog fields surfaced when the API loads the full document-type record
  // (used for synthetic placeholders + workflow defaults in CandidateDocuments).
  kind?: DocumentKind | string | null;
  requested_from?: DocumentRequestedFrom | string | null;
  process_type?: DocumentProcessType | string | null;
  default_expire_in_days?: number | null;
};

export type OrderDraft = {
  ordered_at: string;
  requested_from?: string;
};

export type MetadataFieldConfig = {
  name: string;
  input: "text" | "textarea" | "number" | "date" | "select" | "multiselect" | "boolean";
  enumValues?: string[];
  required: boolean;
};

export type RequiredState = "ready" | "in_progress" | "problem" | "missing";
export type MetadataState = Record<string, any>;

export type CoreFields = {
  number?: string | null;
  issue_date?: string | null;
  expire_date?: string | null;
  ordered_at?: string | null;
  valid_from?: string | null;
  reminder_days_before?: number | null;
  requested_from?: DocumentRequestedFrom;
  owner_id?: string | null;
  comment?: string;
};

