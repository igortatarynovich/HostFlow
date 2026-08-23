/**
 * Constants and configuration for document management
 */

import type { DocumentKind, DocumentStatus, DocumentRequestedFrom, DocumentProcessType } from "../../api/types";
import { DOC_TYPE_LEGACY_ALIASES, EQUIVALENT_TYPE_GROUPS as ALIAS_EQUIVALENT_TYPE_GROUPS } from "../../data/documentTypeAliases";

export const MAX_FILE_MB = 25;
export const MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024;
export const EXPIRING_SOON_THRESHOLD_DAYS = 30;

export const DOCUMENT_STATUS_META: Record<
  DocumentStatus,
  { labelKey: string; color: string; order: number }
> = {
  missing: { labelKey: "admin.documents.status_labels.missing", color: "bg-gray-100 text-gray-700", order: 0 },
  requested: { labelKey: "admin.documents.status_labels.requested", color: "bg-blue-50 text-blue-700", order: 1 },
  in_progress: { labelKey: "admin.documents.status_labels.in_progress", color: "bg-blue-50 text-blue-700", order: 2 },
  received: { labelKey: "admin.documents.status_labels.received", color: "bg-indigo-50 text-indigo-700", order: 3 },
  approved: { labelKey: "admin.documents.status_labels.approved", color: "bg-green-50 text-green-700", order: 4 },
  rejected: { labelKey: "admin.documents.status_labels.rejected", color: "bg-rose-50 text-rose-700", order: 5 },
  expired: { labelKey: "admin.documents.status_labels.expired", color: "bg-amber-50 text-amber-700", order: 6 },
};

export const READINESS_STATE_META: Record<string, { labelKey: string; className: string }> = {
  pending: { labelKey: "admin.documents.readiness_labels.pending", className: "bg-gray-100 text-gray-600" },
  requested: { labelKey: "admin.documents.readiness_labels.requested", className: "bg-blue-50 text-blue-700" },
  ordered: { labelKey: "admin.documents.readiness_labels.ordered", className: "bg-indigo-50 text-indigo-700" },
  in_progress: { labelKey: "admin.documents.readiness_labels.in_progress", className: "bg-sky-50 text-sky-700" },
  awaiting_review: { labelKey: "admin.documents.readiness_labels.awaiting_review", className: "bg-amber-50 text-amber-700" },
  ready: { labelKey: "admin.documents.readiness_labels.ready", className: "bg-green-50 text-green-700" },
  problem: { labelKey: "admin.documents.readiness_labels.problem", className: "bg-rose-50 text-rose-700" },
};

export const KIND_LABEL_KEYS: Record<DocumentKind, string> = {
  driver: "admin.documents.kinds.driver",
  employer: "admin.documents.kinds.employer",
  process: "admin.documents.kinds.process",
};

export const KIND_ORDER: DocumentKind[] = ["driver", "employer", "process"];

export const REQUESTED_FROM_LABEL_KEYS: Record<DocumentRequestedFrom, string> = {
  driver: "admin.documents.requested_from.driver",
  employer: "admin.documents.requested_from.employer",
  agency: "admin.documents.requested_from.agency",
};

export const PROCESS_LABEL_KEYS: Record<DocumentProcessType, string> = {
  none: "admin.documents.process_types.none",
  other: "admin.documents.process_types.other",
  visa: "admin.documents.process_types.visa",
  work_permit: "admin.documents.process_types.work_permit",
  residence_permit: "admin.documents.process_types.residence_permit",
  driver_license: "admin.documents.process_types.driver_license",
  eu_driver_license: "admin.documents.process_types.eu_driver_license",
  adr: "admin.documents.process_types.adr",
  code95: "admin.documents.process_types.code95",
  qualification_code95: "admin.documents.process_types.qualification_code95",
  driver_certificate: "admin.documents.process_types.driver_certificate",
  decision: "admin.documents.process_types.decision",
  residence_card: "admin.documents.process_types.residence_card",
  tachograph_card: "admin.documents.process_types.tachograph_card",
  driver_license_exchange: "admin.documents.process_types.driver_license_exchange",
  swiadectwo_kierowcy: "admin.documents.process_types.swiadectwo_kierowcy",
};

export const READY_STATUSES = new Set<DocumentStatus>(["approved", "received"]);
export const NEGATIVE_STATUSES = new Set<DocumentStatus>(["rejected", "expired"]);

export const EQUIVALENT_TYPE_GROUPS: string[][] = ALIAS_EQUIVALENT_TYPE_GROUPS;

export const REQUIRED_STATUS_META: Record<string, { labelKey: string; className: string }> = {
  ready: { labelKey: "admin.documents.required_status.ready", className: "bg-green-50 text-green-700" },
  in_progress: { labelKey: "admin.documents.required_status.in_progress", className: "bg-blue-50 text-blue-700" },
  problem: { labelKey: "admin.documents.required_status.problem", className: "bg-rose-50 text-rose-700" },
  missing: { labelKey: "admin.documents.required_status.missing", className: "bg-gray-100 text-gray-600" },
};

export const STATUS_FROM_RANK: Record<number, DocumentStatus> = {
  0: "missing",
  1: "requested",
  2: "in_progress",
  3: "received",
  4: "approved",
  5: "rejected",
  6: "expired",
};

export const READINESS_TO_STATUS: Partial<Record<string, DocumentStatus>> = {
  ready: "approved",
  problem: "rejected",
  in_progress: "in_progress",
  pending: "missing",
  requested: "requested",
  ordered: "in_progress",
  awaiting_review: "received",
};

export const CREATION_STATUS_OPTIONS: DocumentStatus[] = [
  "missing",
  "requested",
  "in_progress",
  "received",
  "approved",
  "rejected",
  "expired",
];

export const CORE_METADATA_FIELDS = new Set([
  "number",
  "issue_date",
  "expire_date",
  "ordered_at",
  "valid_from",
  "reminder_days_before",
  "requested_from",
  "owner_id",
  "comment",
]);

export const METADATA_LABEL_NS = "documents.meta_fields";

// Legacy alias strings → canonical registry codes (projection of document-type-legacy-aliases-v1.json).
export const DOC_TYPE_CODE_ALIASES: Record<string, string> = DOC_TYPE_LEGACY_ALIASES;

// Broken default profile often contains only a reduced legacy set; enrich it to full driver flow.
export const DRIVER_DEFAULT_ENRICHMENT_CODES: string[] = [
  "additional_document",
  "adr",
  "code95",
  "decision",
  "work_permit",
  "passport",
  "medical_certificate",
  "driver_license",
  "driver_license_code95",
  "psych_tests",
  "residence_permit",
  "visa",
  "tacho_card",
  "driver_certificate",
];
