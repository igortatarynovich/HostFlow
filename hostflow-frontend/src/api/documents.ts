import { docsApi } from "./client";
import type {
  CandidateDocumentChecklist,
  CandidateDocumentsSummaryResponse,
  Document,
  DocumentCheck,
  DocumentFile,
  DocumentKind,
  DocumentProcessType,
  DocumentReadinessState,
  DocumentReminder,
  DocumentRequestedFrom,
  DocumentStatus,
  DocumentSummary,
  DocumentWorkflow,
  DocumentWorkflowStep,
  DocumentWorkflowStepStatus,
  RulesetDiff,
  RulesetUsageResponse,
  RulesetVersion,
} from "./types";

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

export type PresignUpload =
  { url?: string; method: "POST" | "PUT"; fields?: Record<string, string>; key?: string };

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

// =====================
// Helpers
// =====================

function q<T extends Record<string, any>>(params?: T) {
  return params ? { params } : undefined;
}

function isAxios404(err: any) {
  return !!(err && err.response && err.response.status === 404);
}

function apiErrorMessage(err: any): string {
  const r = err?.response;
  const d = r?.data;
  if (!r) return err?.message || "Network error";
  if (typeof d === "string") return d;
  if (d?.detail) {
    if (typeof d.detail === "string") return d.detail;
    if (Array.isArray(d.detail)) {
      const msgs = d.detail
        .map((x: any) => (typeof x === "string" ? x : x?.msg || x?.message || JSON.stringify(x)))
        .join("; ");
      return msgs || r.statusText || `HTTP ${r.status}`;
    }
    if (typeof d.detail === "object") return d.detail.msg || d.detail.message || JSON.stringify(d.detail);
  }
  return r.statusText || `HTTP ${r.status}`;
}

const DOCUMENT_STATUS_VALUES = [
  "missing",
  "requested",
  "in_progress",
  "received",
  "approved",
  "rejected",
  "expired",
] as const satisfies readonly DocumentStatus[];

const LEGACY_STATUS_MAP: Record<string, DocumentStatus> = {
  planned: "requested",
  pending_validation: "in_progress",
  validation: "in_progress",
  uploaded: "received",
  delivered: "received",
  verified: "approved",
  valid: "approved",
  approved: "approved",
  invalid: "rejected",
  rejected: "rejected",
  expired: "expired",
};

const DOCUMENT_KIND_VALUES: readonly DocumentKind[] = ["driver", "employer", "process"];
const REQUESTED_FROM_VALUES: readonly DocumentRequestedFrom[] = ["driver", "employer", "agency"];
const PROCESS_TYPE_VALUES: readonly DocumentProcessType[] = [
  "none",
  "work_permit",
  "visa",
  "residence_card",
  "tachograph_card",
  "driver_license_exchange",
  "swiadectwo_kierowcy",
  "other",
];

const READINESS_STATE_VALUES = [
  "pending",
  "requested",
  "ordered",
  "in_progress",
  "awaiting_review",
  "ready",
  "problem",
] as const;

const WORKFLOW_STATUS_MAP: Record<string, DocumentWorkflowStepStatus> = {
  completed: "done",
  done: "done",
  approved: "done",
  finished: "done",
  waiting: "waiting",
  on_hold: "paused",
  paused: "paused",
  blocked: "blocked",
  pending: "pending",
  todo: "pending",
  started: "in_progress",
  active: "in_progress",
  in_progress: "in_progress",
};

function isPlainObject(value: unknown): value is Record<string, any> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeStatus(raw: any): DocumentStatus {
  if (typeof raw !== "string") {
    return "requested";
  }
  const trimmed = raw.trim();
  const withoutPrefix = trimmed.replace(/^documentstatus[.:]?/i, "");
  const value = withoutPrefix.toLowerCase();
  if ((DOCUMENT_STATUS_VALUES as readonly string[]).includes(value)) {
    return value as DocumentStatus;
  }
  return LEGACY_STATUS_MAP[value] ?? "requested";
}

function normalizeKind(raw: any): DocumentKind {
  const value = typeof raw === "string" ? raw.toLowerCase() : "";
  if ((DOCUMENT_KIND_VALUES as readonly string[]).includes(value)) {
    return value as DocumentKind;
  }
  return "driver";
}

function normalizeRequestedFrom(raw: any): DocumentRequestedFrom {
  const value = typeof raw === "string" ? raw.toLowerCase() : "";
  if ((REQUESTED_FROM_VALUES as readonly string[]).includes(value)) {
    return value as DocumentRequestedFrom;
  }
  return "driver";
}

function normalizeProcessType(raw: any): DocumentProcessType {
  const value = typeof raw === "string" ? raw.toLowerCase() : "";
  if ((PROCESS_TYPE_VALUES as readonly string[]).includes(value)) {
    return value as DocumentProcessType;
  }
  return "none";
}

function normalizeReadinessState(raw: any): DocumentReadinessState | null {
  if (raw === null || raw === undefined || raw === "") return null;
  const value = String(raw).toLowerCase();
  if ((READINESS_STATE_VALUES as readonly string[]).includes(value)) {
    return value as DocumentReadinessState;
  }
  return value as DocumentReadinessState;
}

function normalizeDateInput(value: any): string | null {
  if (value === null || value === undefined || value === "") return null;
  if (value instanceof Date) return value.toISOString();
  if (typeof value === "number") {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
  }
  return String(value);
}

function normalizeDateTime(value: any): string {
  return normalizeDateInput(value) ?? new Date().toISOString();
}

function normalizeWorkflowStepStatus(raw: any): DocumentWorkflowStepStatus {
  const value = typeof raw === "string" ? raw.toLowerCase() : "";
  if (!value) return "pending";
  return WORKFLOW_STATUS_MAP[value] ?? (value as DocumentWorkflowStepStatus);
}

function normalizeWorkflowStep(raw: any): DocumentWorkflowStep | null {
  if (!isPlainObject(raw) && typeof raw !== "object") return null;
  const code = String(raw?.code ?? "").trim();
  if (!code) return null;
  const title = raw?.title != null ? String(raw.title) : code;
  const status = normalizeWorkflowStepStatus(raw?.status);
  const due_at = normalizeDateInput(raw?.due_at);
  const completed_at = normalizeDateInput(raw?.completed_at);
  const ordered_at = normalizeDateInput(raw?.ordered_at ?? raw?.orderedAt);
  const assignee =
    raw?.assignee != null && String(raw.assignee).trim() ? String(raw.assignee) : undefined;
  const notes = raw?.notes != null && String(raw.notes).trim() ? String(raw.notes) : undefined;
  let due_in_hours: number | undefined | null;
  const rawDueInHours = raw?.due_in_hours ?? raw?.dueInHours;
  if (rawDueInHours === null) {
    due_in_hours = null;
  } else if (typeof rawDueInHours === "number" && Number.isFinite(rawDueInHours)) {
    due_in_hours = rawDueInHours;
  } else if (typeof rawDueInHours === "string" && rawDueInHours.trim()) {
    const parsed = Number(rawDueInHours);
    if (!Number.isNaN(parsed)) due_in_hours = parsed;
  }
  const actor_id =
    raw?.actor_id != null && String(raw.actor_id).trim() ? String(raw.actor_id) : undefined;
  const reminder_id =
    raw?.reminder_id != null && String(raw.reminder_id).trim()
      ? String(raw.reminder_id)
      : undefined;

  return {
    code,
    title,
    status,
    due_at: due_at ?? null,
    due_in_hours: due_in_hours ?? undefined,
    completed_at,
    ordered_at: ordered_at ?? undefined,
    actor_id,
    reminder_id,
    assignee,
    notes,
  };
}

function normalizeDocumentSummary(raw: any): DocumentSummary {
  const source = isPlainObject(raw) ? raw : {};
  const requiredRaw = isPlainObject(source.required) ? source.required : {};

  const expiringSoon = Array.isArray(source.expiring_soon)
    ? source.expiring_soon
        .map((item: any) => {
          if (!item) return null;
          const type = item.type != null ? String(item.type) : "";
          const expires_at = normalizeDateInput(item.expires_at) ?? "";
          if (!type) return null;
          return { type, expires_at };
        })
        .filter((entry): entry is { type: string; expires_at: string } => !!entry)
    : [];

  const readyCount =
    typeof requiredRaw.ready === "number"
      ? requiredRaw.ready
      : typeof requiredRaw.approved === "number"
      ? requiredRaw.approved
      : 0;
  const missingCount =
    typeof requiredRaw.missing_count === "number"
      ? requiredRaw.missing_count
      : Array.isArray(requiredRaw.missing)
      ? requiredRaw.missing.length
      : 0;
  const problemsCount =
    typeof requiredRaw.problems === "number"
      ? requiredRaw.problems
      : Array.isArray(requiredRaw.problematic)
      ? requiredRaw.problematic.length
      : 0;
  const inProgressCount =
    typeof requiredRaw.in_progress === "number"
      ? requiredRaw.in_progress
      : Array.isArray(requiredRaw.in_progress_types)
      ? requiredRaw.in_progress_types.length
      : 0;

  return {
    status: typeof source.status === "string" ? source.status : "missing",
    percent_ready: typeof source.percent_ready === "number" ? source.percent_ready : 0,
    required: {
      total: typeof requiredRaw.total === "number" ? requiredRaw.total : 0,
      approved: typeof requiredRaw.approved === "number" ? requiredRaw.approved : readyCount,
      ready: readyCount,
      in_progress: inProgressCount,
      missing_count: missingCount,
      problems: problemsCount,
      missing: Array.isArray(requiredRaw.missing)
        ? requiredRaw.missing.map((item: any) => String(item))
        : [],
      problematic: Array.isArray(requiredRaw.problematic)
        ? requiredRaw.problematic.map((item: any) => String(item))
        : [],
      ready_types: Array.isArray(requiredRaw.ready_types)
        ? requiredRaw.ready_types.map((item: any) => String(item))
        : undefined,
      in_progress_types: Array.isArray(requiredRaw.in_progress_types)
        ? requiredRaw.in_progress_types.map((item: any) => String(item))
        : undefined,
    },
    expiring_soon: expiringSoon,
    checklist: isPlainObject(source.checklist)
      ? normalizeChecklist(source.checklist)
      : undefined,
  };
}

function normalizeSummaryResponse(raw: any, fallbackCandidateId: string): CandidateDocumentsSummaryResponse {
  const documents = Array.isArray(raw?.documents)
    ? raw.documents.map((item: any) => normalizeDocument(item))
    : [];
  const summary = normalizeDocumentSummary(raw?.summary);
  const candidateId = raw?.candidate_id != null ? String(raw.candidate_id) : fallbackCandidateId;
  const rulesetRaw = isPlainObject(raw?.ruleset_version) ? raw.ruleset_version : {};
  const rulesetVersion: RulesetVersion = {
    id: String((rulesetRaw as any)?.id ?? ""),
    tenant_id: String((rulesetRaw as any)?.tenant_id ?? ""),
    version: Number((rulesetRaw as any)?.version ?? 0),
    ruleset: isPlainObject((rulesetRaw as any)?.ruleset) ? (rulesetRaw as any).ruleset : {},
    comment: (rulesetRaw as any)?.comment ?? null,
    created_by: (rulesetRaw as any)?.created_by ?? null,
    created_at: normalizeDateInput((rulesetRaw as any)?.created_at) ?? "",
    is_active: Boolean((rulesetRaw as any)?.is_active ?? true),
    signature: String((rulesetRaw as any)?.signature ?? ""),
    origin_version_id: (rulesetRaw as any)?.origin_version_id ?? null,
    rollback_comment: (rulesetRaw as any)?.rollback_comment ?? null,
  };

  return {
    candidate_id: candidateId,
    summary,
    documents,
    ruleset_version: rulesetVersion,
    checklist: raw?.checklist ? normalizeChecklist(raw.checklist) : summary.checklist,
  };
}

function normalizeWorkflow(raw: any, processType: DocumentProcessType): DocumentWorkflow {
  const source = isPlainObject(raw) ? raw : {};
  const stepsSource = Array.isArray(source.steps)
    ? source.steps
    : Array.isArray(raw)
    ? raw
    : [];
  const steps = stepsSource
    .map((entry: any) => normalizeWorkflowStep(entry))
    .filter((entry): entry is DocumentWorkflowStep => !!entry);

  const workflowProcessType = normalizeProcessType(source.process_type ?? processType);
  const current_step =
    typeof source.current_step === "string" && source.current_step.trim()
      ? source.current_step
      : null;

  const meta = isPlainObject(source.meta) ? source.meta : undefined;

  return {
    process_type: workflowProcessType,
    steps,
    current_step,
    completed: Boolean(source.completed),
    meta,
  };
}

function normalizeFile(raw: any): DocumentFile | null {
  if (!isPlainObject(raw) && typeof raw !== "object") return null;
  const name = raw?.name ?? raw?.filename ?? raw?.original_name ?? raw?.file_name;
  const url = raw?.url ?? raw?.link ?? raw?.signed_url ?? raw?.download_url ?? null;
  if (!name && !url) return null;
  const sizeValue = raw?.size ?? raw?.bytes ?? raw?.length;
  const versionValue = raw?.version ?? raw?.file_version ?? raw?.v;
  const uploadedBy = raw?.uploaded_by ?? raw?.uploader ?? raw?.created_by;
  return {
    name: name ? String(name) : "document",
    url: url != null ? String(url) : null,
    size: typeof sizeValue === "number" ? sizeValue : sizeValue != null ? Number(sizeValue) : null,
    mime: raw?.mime ?? raw?.content_type ?? raw?.mimetype ?? raw?.type ?? null,
    uploaded_at: normalizeDateInput(raw?.uploaded_at ?? raw?.created_at ?? raw?.timestamp),
    uploaded_by: uploadedBy != null ? String(uploadedBy) : null,
    version: typeof versionValue === "number" ? versionValue : versionValue != null ? Number(versionValue) : null,
  };
}

function normalizeChecklist(raw: any): CandidateDocumentChecklist {
  const source = isPlainObject(raw) ? raw : {};
  const required = Array.isArray(source.requiredTypes)
    ? source.requiredTypes.map((item: any) => String(item))
    : [];
  const optional = Array.isArray(source.optionalTypes)
    ? source.optionalTypes.map((item: any) => String(item))
    : [];
  const debug = isPlainObject(source.debug) ? (source.debug as Record<string, any>) : undefined;
  return {
    requiredTypes: required,
    optionalTypes: optional,
    debug,
  };
}

function normalizeReminder(raw: any): DocumentReminder | null {
  if (!isPlainObject(raw)) return null;
  const due_at = normalizeDateInput(raw.due_at);
  if (!due_at) return null;
  const kindRaw = raw.kind ?? (raw.step_code ? "workflow_step" : "expiry");
  const kind = String(kindRaw) as DocumentReminder["kind"];
  const stepCode = raw.step_code ?? raw?.meta?.step_code;
  return {
    due_at,
    message: raw.message != null ? String(raw.message) : "",
    offset_days: raw.offset_days != null ? Number(raw.offset_days) : 0,
    status: raw.status != null ? String(raw.status) : "pending",
    kind,
    step_code: stepCode != null ? String(stepCode) : null,
  };
}

function normalizeCheck(raw: any): DocumentCheck | null {
  if (!isPlainObject(raw)) return null;
  const decisionRaw = String(raw.decision ?? "").toLowerCase();
  const decision: DocumentCheck["decision"] = decisionRaw === "rejected" ? "rejected" : "approved";
  const payload = isPlainObject(raw.payload) ? raw.payload : null;
  return {
    id: String(raw.id ?? raw.check_id ?? ""),
    document_id: String(raw.document_id ?? raw.doc_id ?? raw.id ?? ""),
    reviewer_id: raw.reviewer_id != null ? String(raw.reviewer_id) : null,
    decision,
    reason_code: raw.reason_code != null ? String(raw.reason_code) : null,
    comment: raw.comment != null ? String(raw.comment) : null,
    payload,
    created_at: normalizeDateTime(raw.created_at),
  };
}

function normalizeDocument<T extends Record<string, any>>(raw: T): Document {
  const docType = String(raw.doc_type ?? raw.type_code ?? raw.type ?? "other") || "other";
  const kind = normalizeKind(raw.kind ?? raw?.meta?.kind);
  const requestedFrom = normalizeRequestedFrom(raw.requested_from ?? raw?.meta?.requested_from);
  const processType = normalizeProcessType(raw.process_type ?? raw?.workflow?.process_type);
  const status = normalizeStatus(raw.status);

  const metaSource = isPlainObject(raw.meta_json)
    ? raw.meta_json
    : isPlainObject(raw.meta)
    ? raw.meta
    : {};
  const meta = { ...metaSource };

  const extraSource = isPlainObject(raw.extra) ? raw.extra : metaSource;
  const extra = extraSource === metaSource ? { ...meta } : { ...extraSource };

  const titleFromPayload =
    raw.title ??
    raw.custom_name ??
    meta.title ??
    meta.document_title ??
    (docType === "other" ? raw.custom_name : undefined);

  const customName =
    raw.custom_name ??
    meta.custom_name ??
    (docType === "other" && titleFromPayload ? titleFromPayload : null);

  const issueDate = normalizeDateInput(raw.issue_date ?? raw.issued_at);
  const expireDate = normalizeDateInput(raw.expire_date ?? raw.expires_at);
  const orderedAt = normalizeDateInput(raw.ordered_at ?? raw.orderedAt);
  const validFrom = normalizeDateInput(raw.valid_from ?? raw.validFrom);

  const files = Array.isArray(raw.files)
    ? raw.files
        .map((entry: any) => normalizeFile(entry))
        .filter((entry): entry is DocumentFile => !!entry)
    : [];
  const hasFiles = typeof raw.has_files === "boolean" ? Boolean(raw.has_files) : files.length > 0;

  const reminders = Array.isArray(raw.reminders)
    ? raw.reminders
        .map((entry: any) => normalizeReminder(entry))
        .filter((entry): entry is DocumentReminder => !!entry)
    : [];

  const lastCheck = normalizeCheck(raw.last_check);
  const workflow = normalizeWorkflow(raw.workflow, processType);
  const readinessState = normalizeReadinessState(raw.readiness_state ?? raw.readinessState);
  const statusRankRaw = raw.status_rank ?? raw.statusRank;
  const statusRankNumber =
    typeof statusRankRaw === "number"
      ? statusRankRaw
      : typeof statusRankRaw === "string" && statusRankRaw.trim()
      ? Number(statusRankRaw)
      : undefined;
  const statusRank = Number.isFinite(statusRankNumber) ? Number(statusRankNumber) : undefined;

  const ownerIdRaw = raw.owner_id ?? raw.candidate_id;

  return {
    id: String(raw.id ?? ""),
    tenant_id: String(raw.tenant_id ?? ""),
    candidate_id: String(raw.candidate_id ?? raw.owner_id ?? ""),
    company_id: raw.company_id != null ? String(raw.company_id) : null,
    kind,
    doc_type: docType,
    type: docType,
    type_code: docType,
    custom_name: customName ?? null,
    title: titleFromPayload != null ? String(titleFromPayload) : null,
    owner_type: raw.owner_type != null ? String(raw.owner_type) : "candidate",
    owner_id: ownerIdRaw != null ? String(ownerIdRaw) : null,
    requested_from: requestedFrom,
    process_type: workflow.process_type,
    number:
      raw.number != null
        ? String(raw.number)
        : meta.number != null
        ? String(meta.number)
        : null,
    status,
    reminder_days_before:
      raw.reminder_days_before != null ? Number(raw.reminder_days_before) : 30,
    files,
    workflow,
    source: raw.source != null ? String(raw.source) : null,
    external_id: raw.external_id != null ? String(raw.external_id) : null,
    verified_at: normalizeDateInput(raw.verified_at),
    issue_date: issueDate,
    expire_date: expireDate,
    issued_at: issueDate,
    expires_at: expireDate,
    ordered_at: orderedAt,
    valid_from: validFrom,
    has_files: hasFiles,
    readiness_state: readinessState ?? null,
    status_rank: statusRank ?? null,
    meta,
    extra,
    meta_json: meta,
    created_at: normalizeDateInput(raw.created_at),
    updated_at: normalizeDateInput(raw.updated_at),
    reminders,
    version: raw.version != null ? Number(raw.version) : null,
    last_check: lastCheck,
  };
}

// =====================
// New API only (/api/v1/db/...)
// =====================

// ---- Catalogs ----
export async function getDocumentTypes(): Promise<DocType[]> {
  const { data } = await docsApi.get<DocType[]>(`/document-types`);
  return data || [];
}

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

export async function listDocuments(opts?: ListDocumentsOptions): Promise<Document[]> {
  const params: Record<string, any> = {};
  const candidateId = opts?.candidateId ?? opts?.candidate_id;
  if (candidateId) params.candidate_id = candidateId;
  const docType = opts?.docType ?? opts?.type ?? opts?.key;
  if (docType) params.doc_type = docType;
  if (opts?.kind) params.kind = opts.kind;
  if (opts?.status) params.status = opts.status;
  if (typeof opts?.ordered === "boolean") params.ordered = opts.ordered;
  if (typeof opts?.limit === "number") params.limit = opts.limit;
  if (typeof opts?.offset === "number") params.offset = opts.offset;
  const config: { params: Record<string, any>; signal?: AbortSignal } = { params };
  if (opts?.signal) config.signal = opts.signal;
  const { data } = await docsApi.get<any[]>(`/documents`, config);
  return (data || []).map((item: any) => normalizeDocument(item));
}

// ---- Documents listing ----
export async function listCandidateDocuments(
  ownerId: string,
  opts?: { includeLastCheck?: boolean; limit?: number; offset?: number }
): Promise<Document[]> {
  const { includeLastCheck = true, limit, offset } = opts || {};
  const { data } = await docsApi.get<any[]>(
    `/candidate/${ownerId}/documents`,
    q({ include_last_check: includeLastCheck, limit, offset })
  );
  return (data || []).map(normalizeDocument);
}

// ---- Single document ----
export async function getDocument(
  docId: string,
  opts?: { includeChecks?: boolean }
): Promise<Document & { checks?: DocumentCheck[] } > {
  const { includeChecks } = opts || {};
  const { data } = await docsApi.get<any>(
    `/documents/${docId}`,
    q({ include_checks: includeChecks })
  );
  const normalized = normalizeDocument(data as any);
  const rawChecks = Array.isArray((data as any)?.checks)
    ? (data as any).checks
        .map((item: any) => normalizeCheck(item))
        .filter(Boolean) as DocumentCheck[]
    : undefined;
  return { ...normalized, checks: rawChecks };
}

export async function listDocumentChecks(docId: string): Promise<DocumentCheck[]> {
  try {
    const { data } = await docsApi.get<any[]>(`/documents/${docId}/checks`);
    return (data || [])
      .map((item: any) => normalizeCheck(item))
      .filter((item): item is DocumentCheck => !!item);
  } catch (err) {
    if (isAxios404(err)) return [];
    throw err;
  }
}

// ---- Create / Patch ----
export async function createCandidateDocument(payload: CreateCandidateDocumentPayload): Promise<Document> {
  if (!payload?.owner_id) {
    throw new Error("owner_id is required to create a document");
  }
  const path = `/candidate/${payload.owner_id}/documents`;
  const resolvedDocType = (
    payload.doc_type ??
    payload.type_code ??
    payload.meta?.doc_type ??
    payload.meta_json?.doc_type ??
    ""
  ).toString().trim();
  if (!resolvedDocType) {
    throw new Error("doc_type (type_code) is required to create a document");
  }

  const issueDate = payload.issue_date ?? payload.issued_at ?? null;
  const expireDate = payload.expire_date ?? payload.expires_at ?? null;

  const metaBase = payload.meta_json ?? payload.meta ?? {};
  const metaPayload: Record<string, any> = isPlainObject(metaBase) ? { ...metaBase } : {};
  if (payload.title !== undefined) {
    metaPayload.title = payload.title;
  }
  if (payload.number !== undefined) {
    metaPayload.number = payload.number;
  }
  if (payload.custom_name !== undefined && payload.custom_name !== null) {
    metaPayload.custom_name = payload.custom_name;
  }

  const body: Record<string, any> = {
    tenant_id: payload.tenant_id,
    candidate_id: payload.owner_id,
    owner_id: payload.owner_id,
    owner_type: payload.owner_type ?? "candidate",
    doc_type: resolvedDocType,
    type: resolvedDocType,
    type_code: resolvedDocType,
  };

  if (payload.kind) body.kind = payload.kind;
  if (payload.requested_from) body.requested_from = payload.requested_from;
  if (payload.process_type) body.process_type = payload.process_type;
  if (payload.company_id !== undefined) body.company_id = payload.company_id;
  if (payload.status) body.status = payload.status;
  if (payload.source) body.source = payload.source;
  if (payload.external_id) body.external_id = payload.external_id;
  if (payload.number !== undefined) body.number = payload.number;
  if (issueDate !== null) body.issue_date = issueDate;
  if (expireDate !== null) body.expire_date = expireDate;
  if (payload.ordered_at) body.ordered_at = payload.ordered_at;
  if (payload.valid_from) body.valid_from = payload.valid_from;
  if (payload.reminder_days_before !== undefined && payload.reminder_days_before !== null) {
    body.reminder_days_before = payload.reminder_days_before;
  }
  if (payload.workflow) body.workflow = payload.workflow;

  const effectiveCustomName =
    payload.custom_name ??
    (resolvedDocType === "other" ? payload.title ?? null : undefined);
  if (effectiveCustomName !== undefined) {
    body.custom_name = effectiveCustomName;
  }

  if (Object.keys(metaPayload).length > 0) {
    body.meta = metaPayload;
  }

  try {
    const { data } = await docsApi.post(path, body);
    return normalizeDocument(data as any);
  } catch (e: any) {
    throw new Error(apiErrorMessage(e));
  }
}

export async function orderDocument(payload: DocumentOrderInput): Promise<Document> {
  if (!payload?.candidate_id) {
    throw new Error("candidate_id is required");
  }
  if (!payload.doc_type) {
    throw new Error("doc_type is required");
  }
  const body: Record<string, any> = {
    candidate_id: payload.candidate_id,
    doc_type: payload.doc_type,
  };
  if (payload.ordered_at) body.ordered_at = payload.ordered_at;
  if (payload.requested_from) body.requested_from = payload.requested_from;
  if (payload.owner_context && Object.keys(payload.owner_context).length > 0) {
    body.owner_context = payload.owner_context;
  }
  const { data } = await docsApi.post(`/documents/order`, body);
  return normalizeDocument(data as any);
}

export async function patchDocument(docId: string, patch: DocumentPatchPayload): Promise<Document> {
  const body: Record<string, any> = {};

  if (patch.doc_type) {
    body.doc_type = patch.doc_type;
    body.type = patch.doc_type;
    body.type_code = patch.doc_type;
  }
  if (patch.kind) body.kind = patch.kind;
  if (patch.requested_from) body.requested_from = patch.requested_from;
  if (patch.process_type) body.process_type = patch.process_type;
  if (patch.custom_name !== undefined) body.custom_name = patch.custom_name;
  if (patch.number !== undefined) body.number = patch.number;
  if (patch.status) body.status = patch.status;
  if (patch.issue_date !== undefined || patch.issued_at !== undefined) {
    body.issue_date = patch.issue_date ?? patch.issued_at ?? null;
  }
  if (patch.expire_date !== undefined || patch.expires_at !== undefined) {
    body.expire_date = patch.expire_date ?? patch.expires_at ?? null;
  }
  if (patch.ordered_at !== undefined) {
    body.ordered_at = patch.ordered_at;
  }
  if (patch.valid_from !== undefined) {
    body.valid_from = patch.valid_from;
  }
  if (patch.reminder_days_before !== undefined) {
    body.reminder_days_before = patch.reminder_days_before;
  }
  if (patch.owner_id !== undefined) body.owner_id = patch.owner_id;
  if (patch.owner_type !== undefined) body.owner_type = patch.owner_type;
  if (patch.company_id !== undefined) body.company_id = patch.company_id;
  if (patch.workflow !== undefined) body.workflow = patch.workflow;
  if (patch.files !== undefined) body.files = patch.files;
  if (patch.source !== undefined) body.source = patch.source;
  if (patch.external_id !== undefined) body.external_id = patch.external_id;

  const metaBase = patch.meta_json ?? patch.meta;
  let metaPayload: Record<string, any> | null = isPlainObject(metaBase) ? { ...metaBase } : null;
  if (patch.title !== undefined) {
    if (!metaPayload) metaPayload = {};
    metaPayload.title = patch.title;
  }
  if (patch.custom_name !== undefined) {
    if (!metaPayload) metaPayload = {};
    metaPayload.custom_name = patch.custom_name;
  }
  if (patch.number !== undefined) {
    if (!metaPayload) metaPayload = {};
    metaPayload.number = patch.number;
  }
  if (metaPayload) {
    body.meta = metaPayload;
  }

  try {
    const { data } = await docsApi.patch(`/documents/${docId}`, body);
    return normalizeDocument(data as any);
  } catch (e: any) {
    throw new Error(apiErrorMessage(e));
  }
}

// ---- Approve/Reject ----
export async function checkDocument(
  docId: string,
  body: {
    reviewer_id?: string;
    decision: "approved" | "rejected";
    reason_code?: string;
    comment?: string;
    payload?: Record<string, any>;
    meta_json?: Record<string, any>;
  }
): Promise<Document> {
  const payload: Record<string, any> = { ...body };
  if (payload.meta_json && !payload.meta) {
    payload.meta = payload.meta_json;
  }
  const { data } = await docsApi.post(`/documents/${docId}/check`, payload);
  return normalizeDocument(data as any);
}

// ---- OCR / Extraction ----
export type ExtractResult = {
  fields: Record<string, any>;
  confidence?: Record<string, number>;
  raw?: any;
  overall_confidence?: number;
};

export async function extractDocument(docId: string): Promise<ExtractResult> {
  try {
    const { data } = await docsApi.post<ExtractResult>(`/documents/${docId}/extract`, {});
    return data || { fields: {} };
  } catch (e: any) {
    // если модуль не отдал extract (например, 404) — не рушим UI
    if (isAxios404(e)) return { fields: {} };
    throw e;
  }
}

// ---- Utils ----
export async function presignUpload(docId: string): Promise<PresignUpload>{
  const { data } = await docsApi.post<PresignUpload>(
    `/documents/${docId}/presign-upload`, {}
  );
  return data;
}

// Фактическая загрузка к presigned url (для реального S3/GCS). В dev используем mockUpload.
export async function uploadViaPresign(presign: PresignUpload, file: File): Promise<Response> {
  if (presign.method === "POST") {
    const fd = new FormData();
    if (presign.fields) {
      for (const [k, v] of Object.entries(presign.fields)) {
        fd.append(k, v);
      }
    }
    fd.append("file", file);
    const resp = await fetch(presign.url!, { method: "POST", body: fd });
    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      throw new Error(`Presign POST failed: ${resp.status} ${text}`);
    }
    return resp;
  } else {
    const resp = await fetch(presign.url!, {
      method: "PUT",
      body: file,
      headers: { "Content-Type": (file.type || "application/octet-stream") }
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      throw new Error(`Presign PUT failed: ${resp.status} ${text}`);
    }
    return resp;
  }
}

// ---- Local dev helper (mock upload to local storage) ----
export async function mockUpload(params: { key: string; file: File | Blob }): Promise<{ ok: boolean; stored_as: string }> {
  const fd = new FormData();
  fd.append("key", params.key);
  fd.append("file", params.file);
  const { data } = await docsApi.post<{ ok: boolean; stored_as: string; url?: string; version?: number }>(
    "/mock-upload",
    fd,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function getSummary(
  ownerId: string,
  opts?: { context?: Record<string, any> | null; fillMissing?: boolean }
): Promise<CandidateDocumentsSummaryResponse> {
  const params: Record<string, any> = {};
  if (opts?.context && Object.keys(opts.context).length > 0) {
    try {
      params.owner_context = JSON.stringify(opts.context);
    } catch {
      /* ignore invalid context serialization */
    }
  }
  if (opts?.fillMissing !== undefined) {
    params.fill_missing = opts.fillMissing;
  }

  const { data } = await docsApi.get<any>(`/candidate/${ownerId}/documents/summary`, {
    params: Object.keys(params).length ? params : undefined,
  });

  const normalized = normalizeSummaryResponse(data, ownerId);
  if (!normalized.summary.checklist && data?.summary?.checklist) {
    normalized.summary.checklist = data.summary.checklist;
  }
  if (!normalized.checklist) {
    normalized.checklist = data?.checklist ?? normalized.summary.checklist ?? {
      requiredTypes: [],
      optionalTypes: [],
    };
  }
  return normalized;
}

export async function getChecklist(
  ownerId: string,
  context?: Record<string, any>
): Promise<CandidateDocumentChecklist> {
  const { data } = await docsApi.get<any>(
    `/candidate/${ownerId}/checklist`,
    q(context ? { owner_context: JSON.stringify(context) } : undefined)
  );
  return {
    requiredTypes: Array.isArray(data?.requiredTypes)
      ? data.requiredTypes.map((item: any) => String(item))
      : [],
    optionalTypes: Array.isArray(data?.optionalTypes)
      ? data.optionalTypes.map((item: any) => String(item))
      : [],
    debug: isPlainObject(data?.debug) ? data.debug : undefined,
  };
}

export async function exportDocumentsJSON(ownerId: string) {
  const { data } = await docsApi.get<any>(`/candidate/${ownerId}/documents/export.json`);
  return data;
}

export async function exportDocumentsCSV(ownerId: string): Promise<Blob> {
  const { data } = await docsApi.get<Blob>(`/candidate/${ownerId}/documents/export.csv`, {
    responseType: "blob",
  });
  return data;
}

// ---- Delete ----
export async function deleteDocument(docId: string): Promise<void> {
  await docsApi.delete(`/documents/${docId}`);
}

// ---- File download / open ----
export type DocumentFileDownload = {
  blob: Blob;
  filename?: string | null;
  contentType?: string | null;
};

const parseContentDisposition = (value: string | null | undefined): string | null => {
  if (!value) return null;
  const match = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(value);
  if (!match || !match[1]) return null;
  try {
    return decodeURIComponent(match[1].replace(/["']/g, ""));
  } catch {
    return match[1].replace(/["']/g, "");
  }
};

export async function downloadDocumentFile(docId: string): Promise<DocumentFileDownload> {
  const response = await docsApi.get<Blob>(`/documents/${docId}/file`, {
    responseType: "blob",
  });
  const headers = response.headers as any;
  const getHeader = (name: string): string | undefined => {
    if (!headers) return undefined;
    if (typeof headers.get === "function") {
      const direct = headers.get(name);
      if (direct) return direct;
    }
    return headers[name] ?? headers[name.toLowerCase()] ?? headers[name.toUpperCase()];
  };
  const disposition = getHeader("content-disposition");
  const contentType = getHeader("content-type");
  return {
    blob: response.data,
    filename: parseContentDisposition(disposition),
    contentType: typeof contentType === "string" ? contentType : null,
  };
}

export async function getDocumentFileUrl(docId: string): Promise<{ url: string; expires_at?: string }>{
  const { data } = await docsApi.get<{ url: string; expires_at?: string }>(
    `/documents/${docId}/file-url`
  );
  return data;
}

// ---- Meta schemas ----
// Устойчивый фетч: сначала /meta-schema, если 404 — пробуем /schema
export async function getMetaSchema(type_code: string): Promise<any> {
  if (!type_code) throw new Error("type_code is empty");
  try {
    const { data } = await docsApi.get<any>(`/document-types/${type_code}/meta-schema`);
    return data;
  } catch (e) {
    if (isAxios404(e)) {
      const { data } = await docsApi.get<any>(`/document-types/${type_code}/schema`);
      return data;
    }
    throw e;
  }
}

// Серверная валидация: основной путь /validate-meta,
// если 404 — мягкий фолбэк (считаем валидным, бэкенд всё равно проверит на PATCH)
export async function validateMeta(
  type_code: string,
  meta: Record<string, any>
): Promise<{ valid: boolean; errors?: any[] }>{
  if (!type_code) return { valid: true, errors: [] };
  try {
    const { data } = await docsApi.post<{ valid: boolean; errors?: any[] }>(
      `/document-types/${type_code}/validate-meta`,
      meta
    );
    return data;
  } catch (e) {
    if (isAxios404(e)) {
      return { valid: true, errors: [] };
    }
    throw e;
  }
}

// ---- Ruleset (для summary/checklist) ----
export async function getRuleset(): Promise<RulesetVersion> {
  const { data } = await docsApi.get<RulesetVersion>(`/ruleset`);
  return data;
}

export async function patchRuleset(body: any): Promise<RulesetVersion> {
  const { data } = await docsApi.patch<RulesetVersion>(`/ruleset`, body);
  return data;
}

export const putRuleset = patchRuleset;

export async function listRulesetVersions(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<RulesetVersion[]> {
  const { data } = await docsApi.get<RulesetVersion[]>(`/ruleset/versions`, q(params));
  return data;
}

export async function getRulesetVersionById(id: string): Promise<RulesetVersion> {
  const { data } = await docsApi.get<RulesetVersion>(`/ruleset/versions/${id}`);
  return data;
}

export async function createRulesetVersion(
  payload: RulesetVersionCreateInput
): Promise<RulesetVersion> {
  const { data } = await docsApi.post<RulesetVersion>(`/ruleset/versions`, payload);
  return data;
}

export async function activateRulesetVersion(id: string): Promise<RulesetVersion> {
  const { data } = await docsApi.post<RulesetVersion>(`/ruleset/versions/${id}/activate`, {});
  return data;
}

export async function rollbackRulesetVersion(
  id: string,
  payload: RulesetRollbackInput
): Promise<RulesetVersion> {
  const { data } = await docsApi.post<RulesetVersion>(
    `/ruleset/versions/${id}/rollback`,
    payload
  );
  return data;
}

export async function getRulesetDiff(
  id: string,
  compareTo?: string | null
): Promise<RulesetDiff> {
  const { data } = await docsApi.get<RulesetDiff>(`/ruleset/versions/${id}/diff`, q(
    compareTo ? { compare_to: compareTo } : undefined
  ));
  return data;
}

export async function getRulesetUsage(
  params?: { used_in?: string; since?: string; until?: string; limit?: number }
): Promise<RulesetUsageResponse> {
  const { data } = await docsApi.get<RulesetUsageResponse>(`/ruleset/usage`, q(params));
  return data;
}

// Backward-compat
export const postDocumentCheck = checkDocument;
