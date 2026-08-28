import type {
  CandidateDocumentChecklist,
  CandidateDocumentsSummaryResponse,
  Document,
  DocumentCheck,
  DocumentFile,
  DocumentKind,
  DocumentPackProjection,
  DocumentProcessType,
  DocumentReadinessState,
  DocumentReminder,
  DocumentRequestedFrom,
  DocumentStatus,
  DocumentSummary,
  DocumentWorkflow,
  DocumentWorkflowStep,
  DocumentWorkflowStepStatus,
  OwnerExpiryAggregate,
  ReminderWorkQueueAction,
  ReminderWorkQueueItem,
  ReminderWorkQueueSeverity,
  RulesetVersion,
} from "../types";
import { isPlainObject } from "./helpers";

// Constants
export const DOCUMENT_STATUS_VALUES = [
  "missing",
  "requested",
  "in_progress",
  "received",
  "approved",
  "rejected",
  "expired",
] as const satisfies readonly DocumentStatus[];

export const LEGACY_STATUS_MAP: Record<string, DocumentStatus> = {
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

export const DOCUMENT_KIND_VALUES: readonly DocumentKind[] = ["driver", "employer", "process"];
export const REQUESTED_FROM_VALUES: readonly DocumentRequestedFrom[] = ["driver", "employer", "agency"];
export const PROCESS_TYPE_VALUES: readonly DocumentProcessType[] = [
  "none",
  "work_permit",
  "visa",
  "residence_card",
  "tachograph_card",
  "driver_license_exchange",
  "swiadectwo_kierowcy",
  "other",
];

export const READINESS_STATE_VALUES = [
  "pending",
  "requested",
  "ordered",
  "in_progress",
  "awaiting_review",
  "ready",
  "problem",
] as const;

export const WORKFLOW_STATUS_MAP: Record<string, DocumentWorkflowStepStatus> = {
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

// Normalization functions
export function normalizeStatus(raw: any): DocumentStatus {
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

export function normalizeKind(raw: any): DocumentKind {
  const value = typeof raw === "string" ? raw.toLowerCase() : "";
  if ((DOCUMENT_KIND_VALUES as readonly string[]).includes(value)) {
    return value as DocumentKind;
  }
  return "driver";
}

export function normalizeRequestedFrom(raw: any): DocumentRequestedFrom {
  const value = typeof raw === "string" ? raw.toLowerCase() : "";
  if ((REQUESTED_FROM_VALUES as readonly string[]).includes(value)) {
    return value as DocumentRequestedFrom;
  }
  return "driver";
}

export function normalizeProcessType(raw: any): DocumentProcessType {
  const value = typeof raw === "string" ? raw.toLowerCase() : "";
  if ((PROCESS_TYPE_VALUES as readonly string[]).includes(value)) {
    return value as DocumentProcessType;
  }
  return "none";
}

export function normalizeReadinessState(raw: any): DocumentReadinessState | null {
  if (raw === null || raw === undefined || raw === "") return null;
  const value = String(raw).toLowerCase();
  if ((READINESS_STATE_VALUES as readonly string[]).includes(value)) {
    return value as DocumentReadinessState;
  }
  return value as DocumentReadinessState;
}

export function normalizeDateInput(value: any): string | null {
  if (value === null || value === undefined || value === "") return null;
  if (value instanceof Date) return value.toISOString();
  if (typeof value === "number") {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
  }
  return String(value);
}

export function normalizeDateTime(value: any): string {
  return normalizeDateInput(value) ?? new Date().toISOString();
}

export function normalizeWorkflowStepStatus(raw: any): DocumentWorkflowStepStatus {
  const value = typeof raw === "string" ? raw.toLowerCase() : "";
  if (!value) return "pending";
  return WORKFLOW_STATUS_MAP[value] ?? (value as DocumentWorkflowStepStatus);
}

export function normalizeWorkflowStep(raw: any): DocumentWorkflowStep | null {
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

function normalizeOwnerExpiryAggregate(raw: any): OwnerExpiryAggregate | undefined {
  if (!isPlainObject(raw)) return undefined;
  return {
    all_documents_valid: Boolean(raw.all_documents_valid),
    has_expiring_documents: Boolean(raw.has_expiring_documents),
    has_expired_documents: Boolean(raw.has_expired_documents),
    has_missing_expiry: Boolean(raw.has_missing_expiry),
  };
}

export function normalizeDocumentPackProjection(raw: any): DocumentPackProjection | null {
  if (!isPlainObject(raw) || !raw.code) return null;
  const status = String(raw.status || "valid");
  const packStatus =
    status === "gaps" || status === "warnings" || status === "skeleton" || status === "valid"
      ? status
      : "valid";
  return {
    code: String(raw.code),
    label: String(raw.label || raw.code),
    status: packStatus,
    skeleton: Boolean(raw.skeleton),
    applies: Boolean(raw.applies),
    ref_pack_codes: Array.isArray(raw.ref_pack_codes)
      ? raw.ref_pack_codes.map((item: any) => String(item))
      : [],
    required: Array.isArray(raw.required) ? raw.required.map((item: any) => String(item)) : [],
    present: Array.isArray(raw.present) ? raw.present.map((item: any) => String(item)) : [],
    missing: Array.isArray(raw.missing) ? raw.missing.map((item: any) => String(item)) : [],
    expired: Array.isArray(raw.expired) ? raw.expired.map((item: any) => String(item)) : [],
    expiring_soon: Array.isArray(raw.expiring_soon)
      ? raw.expiring_soon
          .map((item: any) => {
            if (!isPlainObject(item)) return null;
            return {
              document_code: String(item.document_code || ""),
              expires_on: normalizeDateInput(item.expires_on),
              days_left: typeof item.days_left === "number" ? item.days_left : null,
            };
          })
          .filter((item): item is NonNullable<typeof item> => Boolean(item?.document_code))
      : [],
    missing_expiry: Array.isArray(raw.missing_expiry)
      ? raw.missing_expiry.map((item: any) => String(item))
      : [],
    gaps: Array.isArray(raw.gaps) ? raw.gaps.map((item: any) => String(item)) : [],
    blockers: Array.isArray(raw.blockers) ? raw.blockers.map((item: any) => String(item)) : [],
    warnings: Array.isArray(raw.warnings) ? raw.warnings.map((item: any) => String(item)) : [],
    expiry: normalizeOwnerExpiryAggregate(raw.expiry) || {
      all_documents_valid: true,
      has_expiring_documents: false,
      has_expired_documents: false,
      has_missing_expiry: false,
    },
  };
}

const REMINDER_WORK_QUEUE_ACTIONS = new Set<ReminderWorkQueueAction>([
  "upload_document",
  "request_update",
  "renew_document",
  "capture_expiry_date",
]);

const REMINDER_WORK_QUEUE_SEVERITIES = new Set<ReminderWorkQueueSeverity>([
  "critical",
  "high",
  "medium",
  "low",
]);

export function normalizeReminderWorkQueueItem(raw: any): ReminderWorkQueueItem | null {
  if (!isPlainObject(raw)) return null;
  const taskKey = String(raw.task_key || "").trim();
  const documentCode = String(raw.document_code || "").trim();
  if (!taskKey || !documentCode) return null;

  const actionRaw = String(raw.action || "");
  const action = REMINDER_WORK_QUEUE_ACTIONS.has(actionRaw as ReminderWorkQueueAction)
    ? (actionRaw as ReminderWorkQueueAction)
    : "upload_document";

  const severityRaw = String(raw.severity || "low");
  const severity = REMINDER_WORK_QUEUE_SEVERITIES.has(severityRaw as ReminderWorkQueueSeverity)
    ? (severityRaw as ReminderWorkQueueSeverity)
    : "low";

  const ownerTypeRaw = String(raw.owner_type || "candidate");
  const ownerType = ownerTypeRaw === "employee" ? "employee" : "candidate";

  return {
    task_key: taskKey,
    title: String(raw.title || documentCode),
    severity,
    owner_type: ownerType,
    owner_id: String(raw.owner_id || ""),
    recipient_role: String(raw.recipient_role || ""),
    due_date: normalizeDateInput(raw.due_date),
    source_pack: String(raw.source_pack || ""),
    action,
    document_code: documentCode,
    reason: String(raw.reason || ""),
  };
}

export function normalizeDocumentSummary(raw: any): DocumentSummary {
  const source = isPlainObject(raw) ? raw : {};
  const requiredRaw = isPlainObject(source.required) ? source.required : {};

  const expiringSoon = Array.isArray(source.expiring_soon)
    ? source.expiring_soon
        .map((item: any) => {
          if (!item) return null;
          const type = item.type != null ? String(item.type) : "";
          const expires_at = normalizeDateInput(item.expires_at) ?? "";
          if (!type) return null;
          return {
            type,
            expires_at,
            days_left: typeof item.days_left === "number" ? item.days_left : null,
          };
        })
        .filter((entry): entry is { type: string; expires_at: string; days_left?: number | null } => !!entry)
    : [];

  const expired = Array.isArray(source.expired)
    ? source.expired
        .map((item: any) => {
          if (!item) return null;
          const type = item.type != null ? String(item.type) : "";
          if (!type) return null;
          return {
            type,
            expires_at: normalizeDateInput(item.expires_at),
            days_left: typeof item.days_left === "number" ? item.days_left : null,
          };
        })
        .filter((entry): entry is { type: string; expires_at?: string | null; days_left?: number | null } => !!entry)
    : undefined;

  const missingExpiry = Array.isArray(source.missing_expiry)
    ? source.missing_expiry
        .map((item: any) => {
          if (!item) return null;
          const type = item.type != null ? String(item.type) : "";
          return type ? { type } : null;
        })
        .filter((entry): entry is { type: string } => !!entry)
    : undefined;

  const packs = Array.isArray(source.packs)
    ? source.packs
        .map((item: any) => normalizeDocumentPackProjection(item))
        .filter((item): item is DocumentPackProjection => item != null)
    : undefined;

  const reminderWorkQueue = Array.isArray(source.reminder_work_queue)
    ? source.reminder_work_queue
        .map((item: any) => normalizeReminderWorkQueueItem(item))
        .filter((item): item is ReminderWorkQueueItem => item != null)
    : undefined;

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
    expired,
    missing_expiry: missingExpiry,
    expiry: normalizeOwnerExpiryAggregate(source.expiry),
    packs,
    reminder_work_queue: reminderWorkQueue,
    checklist: isPlainObject(source.checklist)
      ? normalizeChecklist(source.checklist)
      : undefined,
  };
}

export function normalizeSummaryResponse(
  raw: any,
  fallbackCandidateId: string
): CandidateDocumentsSummaryResponse {
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

export function normalizeWorkflow(
  raw: any,
  processType: DocumentProcessType
): DocumentWorkflow {
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

export function normalizeFile(raw: any): DocumentFile | null {
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
    version:
      typeof versionValue === "number"
        ? versionValue
        : versionValue != null
        ? Number(versionValue)
        : null,
  };
}

export function normalizeChecklist(raw: any): CandidateDocumentChecklist {
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

export function normalizeReminder(raw: any): DocumentReminder | null {
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

export function normalizeCheck(raw: any): DocumentCheck | null {
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

export function normalizeDocument<T extends Record<string, any>>(raw: T): Document {
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
  const hasFiles =
    files.length > 0 ||
    (typeof raw.has_files === "boolean"
      ? Boolean(raw.has_files)
      : Boolean(raw.path || raw.filename));
  const documentRuntime = isPlainObject(raw.document_runtime) ? raw.document_runtime : null;

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
    document_runtime: documentRuntime,
  };
}

