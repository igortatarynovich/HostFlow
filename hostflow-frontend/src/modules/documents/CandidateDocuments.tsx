import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import {
  getDocumentTypes,
  getSummary,
  createCandidateDocument,
  deleteDocument,
  getDocumentFileUrl,
  downloadDocumentFile,
  presignUpload,
  mockUpload,
  patchDocument,
  checkDocument,
  listDocuments,
  orderDocument,
} from "../../api/documents";
import type {
  Document,
  DocumentKind,
  DocumentStatus,
  DocumentRequestedFrom,
  DocumentProcessType,
  DocumentCheck,
  DocumentWorkflow,
  DocumentWorkflowStep,
  DocumentReminder,
  CandidateDocumentsSummaryResponse,
} from "../../api/types";
import type { CreateCandidateDocumentPayload, DocumentPatchPayload, DocumentOrderInput } from "../../api/documents";
import { usePermissions } from "../../hooks/usePermissions";
import { docsApi } from "../../api/client";
import { useI18n } from "../../i18n";

const MAX_FILE_MB = 25;
const MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024;

type DocType = {
  id?: string;
  code: string;
  name?: string;
  required?: boolean;
  meta_schema?: any;
  metadata_schema?: Record<string, any> | null;
  required_files?: Record<string, any> | null;
  orderable?: boolean | null;
};

type OrderDraft = {
  ordered_at: string;
  requested_from?: string;
};

type MetadataFieldConfig = {
  name: string;
  input: "text" | "textarea" | "number" | "date" | "select" | "multiselect" | "boolean";
  enumValues?: string[];
  required: boolean;
};

const DOCUMENT_STATUS_META: Record<
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

const READINESS_STATE_META: Record<string, { labelKey: string; className: string }> = {
  pending: { labelKey: "admin.documents.readiness_labels.pending", className: "bg-gray-100 text-gray-600" },
  requested: { labelKey: "admin.documents.readiness_labels.requested", className: "bg-blue-50 text-blue-700" },
  ordered: { labelKey: "admin.documents.readiness_labels.ordered", className: "bg-indigo-50 text-indigo-700" },
  in_progress: { labelKey: "admin.documents.readiness_labels.in_progress", className: "bg-sky-50 text-sky-700" },
  awaiting_review: { labelKey: "admin.documents.readiness_labels.awaiting_review", className: "bg-amber-50 text-amber-700" },
  ready: { labelKey: "admin.documents.readiness_labels.ready", className: "bg-green-50 text-green-700" },
  problem: { labelKey: "admin.documents.readiness_labels.problem", className: "bg-rose-50 text-rose-700" },
};

const KIND_LABEL_KEYS: Record<DocumentKind, string> = {
  driver: "admin.documents.kinds.driver",
  employer: "admin.documents.kinds.employer",
  process: "admin.documents.kinds.process",
};

const KIND_ORDER: DocumentKind[] = ["driver", "employer", "process"];

const REQUESTED_FROM_LABEL_KEYS: Record<DocumentRequestedFrom, string> = {
  driver: "admin.documents.requested_from.driver",
  employer: "admin.documents.requested_from.employer",
  agency: "admin.documents.requested_from.agency",
};

const PROCESS_LABEL_KEYS: Record<DocumentProcessType, string> = {
  none: "admin.documents.process_types.none",
  work_permit: "admin.documents.process_types.work_permit",
  visa: "admin.documents.process_types.visa",
  residence_card: "admin.documents.process_types.residence_card",
  tachograph_card: "admin.documents.process_types.tachograph_card",
  driver_license_exchange: "admin.documents.process_types.driver_license_exchange",
  swiadectwo_kierowcy: "admin.documents.process_types.swiadectwo_kierowcy",
  other: "admin.documents.process_types.other",
};

const READY_STATUSES = new Set<DocumentStatus>(["approved", "received"]);
const NEGATIVE_STATUSES = new Set<DocumentStatus>(["rejected", "expired"]);
const EQUIVALENT_TYPE_GROUPS: string[][] = [
  ["driver_license", "code95", "driver_license_code95", "eu_driver_license_code95"],
];
const EXPIRING_SOON_THRESHOLD_DAYS = 30;

type RequiredState = "ready" | "in_progress" | "problem" | "missing";
type MetadataState = Record<string, any>;

const CORE_METADATA_FIELDS = new Set([
  "number",
  "issued_at",
  "expires_at",
  "ordered_at",
  "valid_from",
  "valid_to",
  "reminder_days_before",
  "requested_from",
  "owner_id",
  "comment",
]);

const METADATA_LABEL_NS = "documents.meta_fields";

const extractMetadataFields = (schema?: Record<string, any> | null): MetadataFieldConfig[] => {
  if (!schema || typeof schema !== "object") return [];
  if ((schema.type && schema.type !== "object") || typeof schema.properties !== "object") return [];
  const required = new Set<string>(
    Array.isArray(schema.required) ? schema.required.map((item) => String(item)) : []
  );
  return Object.entries(schema.properties).reduce<MetadataFieldConfig[]>((acc, [name, config]) => {
    if (CORE_METADATA_FIELDS.has(name)) {
      return acc;
    }
    const fieldSchema =
      (typeof config === "object" && config ? config : {}) as Record<string, any>;
    let input: MetadataFieldConfig["input"] = "text";
    let enumValues: string[] | undefined;
    if (Array.isArray(fieldSchema.enum) && fieldSchema.enum.length > 0) {
      input = "select";
      enumValues = fieldSchema.enum.map((item: any) => String(item));
    }
    if (
      fieldSchema.type === "array" &&
      typeof fieldSchema.items === "object" &&
      Array.isArray(fieldSchema.items?.enum)
    ) {
      input = "multiselect";
      enumValues = fieldSchema.items.enum.map((item: any) => String(item));
    } else if (fieldSchema.type === "number" || fieldSchema.type === "integer") {
      input = "number";
    } else if (fieldSchema.type === "boolean") {
      input = "boolean";
    } else if (fieldSchema.format === "date") {
      input = "date";
    }
    acc.push({
      name,
      input,
      enumValues,
      required: required.has(name),
    });
    return acc;
  }, []);
};

const defaultMetadataValue = (field: MetadataFieldConfig) => {
  switch (field.input) {
    case "number":
      return "";
    case "date":
      return "";
    case "multiselect":
      return [] as string[];
    case "boolean":
      return false;
    default:
      return "";
  }
};

const normalizeMetadataValue = (field: MetadataFieldConfig, value: any) => {
  if (field.input === "multiselect") {
    return Array.isArray(value) ? value.map((item) => String(item)) : [];
  }
  if (field.input === "boolean") {
    return Boolean(value);
  }
  if (field.input === "number") {
    if (value === null || value === "" || value === undefined) return null;
    const parsed = Number(value);
    return Number.isNaN(parsed) ? null : parsed;
  }
  if (field.input === "date") {
    if (!value) return null;
    return String(value).slice(0, 10);
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || null;
  }
  return value ?? null;
};

const buildMetadataDefaults = (fields: MetadataFieldConfig[]): MetadataState => {
  const base: MetadataState = {};
  fields.forEach((field) => {
    base[field.name] = defaultMetadataValue(field);
  });
  return base;
};

const buildMetadataStateFromDoc = (doc: Document, fields: MetadataFieldConfig[]): MetadataState => {
  const base: MetadataState = {};
  const source = doc.meta_json ?? {};
  fields.forEach((field) => {
    const rawValue =
      source[field.name] !== undefined
        ? source[field.name]
        : (doc as Record<string, any>)[field.name];
    if (field.input === "multiselect") {
      base[field.name] = Array.isArray(rawValue)
        ? rawValue.map((item) => String(item))
        : (defaultMetadataValue(field) as string[]);
    } else if (field.input === "boolean") {
      base[field.name] = Boolean(rawValue);
    } else if (field.input === "number") {
      if (typeof rawValue === "number") {
        base[field.name] = rawValue;
      } else if (typeof rawValue === "string" && rawValue.trim()) {
        const parsed = Number(rawValue);
        base[field.name] = Number.isNaN(parsed) ? "" : parsed;
      } else {
        base[field.name] = "";
      }
    } else if (field.input === "date") {
      base[field.name] = rawValue ? String(rawValue).slice(0, 10) : "";
    } else {
      base[field.name] = typeof rawValue === "string" ? rawValue : rawValue ?? "";
    }
  });
  return base;
};

const buildMetadataPayloadFromState = (
  fields: MetadataFieldConfig[],
  state: MetadataState | undefined
): Record<string, any> => {
  const payload: Record<string, any> = {};
  fields.forEach((field) => {
    const source = state ? state[field.name] : undefined;
    const normalized = normalizeMetadataValue(field, source);
    if (
      normalized !== null &&
      normalized !== "" &&
      !(Array.isArray(normalized) && normalized.length === 0)
    ) {
      payload[field.name] = normalized;
    } else {
      delete payload[field.name];
    }
  });
  return payload;
};

const STATUS_FROM_RANK: Record<number, DocumentStatus> = {
  0: "missing",
  1: "requested",
  2: "in_progress",
  3: "in_progress",
  4: "received",
  5: "received",
  6: "approved",
  7: "approved",
  8: "expired",
  9: "rejected",
  10: "expired",
};

const READINESS_TO_STATUS: Partial<Record<string, DocumentStatus>> = {
  ready: "approved",
  ordered: "requested",
  in_progress: "in_progress",
  awaiting_review: "in_progress",
  requested: "requested",
  problem: "rejected",
};

const defaultOrderDraft = (docType: string): OrderDraft => {
  const base: OrderDraft = { ordered_at: computeTodayIso() };
  if (docType === "work_permit") {
    base.requested_from = computeTodayIso();
  }
  return base;
};

const resolveRequestedFromDate = (doc: Document): string | null => {
  const sources = [doc.meta_json, doc.meta] as Array<Record<string, any> | null | undefined>;
  for (const source of sources) {
    if (source && typeof source === "object") {
      const raw = source.requested_from_date ?? source.requested_from;
      if (raw) {
        const value = String(raw).trim();
        if (value) return value;
      }
    }
  }
  return null;
};

const effectiveStatus = (doc: Document): DocumentStatus => {
  const raw = doc.status as DocumentStatus | undefined;
  if (raw && DOCUMENT_STATUS_META[raw]) {
    return raw;
  }
  if (doc.readiness_state) {
    const mapped = READINESS_TO_STATUS[doc.readiness_state];
    if (mapped) return mapped;
  }
  if (typeof doc.status_rank === "number") {
    const mapped = STATUS_FROM_RANK[doc.status_rank];
    if (mapped) return mapped;
  }
  return "requested";
};

// --- helper: prefer backend status over heuristics ---
const normalizeStatus = (value: any): DocumentStatus | null => {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  const matched = /^documentstatus[.:]?(.+)$/i.exec(trimmed);
  const normalized = (matched ? matched[1] : trimmed).toLowerCase();
  return (DOCUMENT_STATUS_META as Record<string, any>)[normalized]
    ? (normalized as DocumentStatus)
    : null;
};

const primaryStatus = (doc: Document): DocumentStatus => {
  const normalized = normalizeStatus(doc.status);
  if (normalized) return normalized;
  return effectiveStatus(doc);
};



const CREATION_STATUS_OPTIONS: DocumentStatus[] = [
  "requested",
  "in_progress",
  "received",
  "approved",
];

const computeTodayIso = (): string => new Date().toISOString().slice(0, 10);

const REQUIRED_STATUS_META: Record<RequiredState, { labelKey: string; className: string }> = {
  ready: { labelKey: "admin.documents.readiness_labels.ready", className: "bg-green-100 text-green-700" },
  in_progress: { labelKey: "admin.documents.readiness_labels.in_progress", className: "bg-blue-100 text-blue-700" },
  problem: { labelKey: "admin.documents.readiness_labels.problem", className: "bg-rose-100 text-rose-700" },
  missing: { labelKey: "admin.documents.readiness_labels.pending", className: "bg-gray-100 text-gray-600" },
};

type CoreFields = {
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

const toArray = <T,>(value: any): T[] => {
  if (Array.isArray(value)) return value as T[];
  if (Array.isArray(value?.items)) return value.items as T[];
  if (Array.isArray(value?.data)) return value.data as T[];
  return [];
};

const isTooLarge = (file?: File | null) => !!file && file.size > MAX_FILE_BYTES;

const formatDate = (value?: string | null) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString();
};

const formatDateTime = (value?: string | null) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
};

const dateValue = (value?: string | null) => {
  if (!value) return 0;
  const time = Date.parse(value);
  return Number.isNaN(time) ? 0 : time;
};

const daysUntil = (value?: string | null) => {
  if (!value) return null;
  const target = Date.parse(value);
  if (Number.isNaN(target)) return null;
  const now = new Date();
  const startOfToday = Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate()
  );
  const diffMs = target - startOfToday;
  return Math.floor(diffMs / (24 * 60 * 60 * 1000));
};

const resolveDocumentUrl = (link: string): string => {
  if (!link) return link;
  try {
    return new URL(link).toString();
  } catch {
    const base =
      docsApi?.defaults?.baseURL ||
      (typeof window !== "undefined" ? window.location.origin : undefined);
    if (!base) return link;
    try {
      return new URL(link, base).toString();
    } catch {
      return link;
    }
  }
};

const guessPreviewable = (contentType: string | null | undefined, filename?: string | null) => {
  const mime = (contentType || "").toLowerCase();
  if (mime.startsWith("image/") || mime === "application/pdf") return true;
  if (filename) {
    const lower = filename.toLowerCase();
    return lower.endsWith(".pdf") || lower.endsWith(".jpg") || lower.endsWith(".jpeg") || lower.endsWith(".png");
  }
  return false;
};

const detectPreviewMime = (contentType: string | null | undefined, filename?: string | null) => {
  const lowerType = (contentType || "").toLowerCase();
  if (lowerType) return lowerType;
  if (!filename) return null;
  const lower = filename.toLowerCase();
  if (lower.endsWith(".pdf")) return "application/pdf";
  if (lower.endsWith(".png")) return "image/png";
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
  return null;
};

const filenameFromUrl = (value: string | null | undefined): string | null => {
  if (!value) return null;
  try {
    const parsed = new URL(value);
    const segments = parsed.pathname.split("/");
    const last = segments[segments.length - 1];
    return last ? decodeURIComponent(last) : null;
  } catch {
    const segments = String(value).split("/");
    const last = segments[segments.length - 1];
    return last || null;
  }
};

const isProbablyHtmlBlob = async (blob: Blob, contentType?: string | null): Promise<boolean> => {
  const type = (contentType || blob.type || "").toLowerCase();
  if (type.includes("html")) return true;
  if (type.startsWith("text/") && !type.includes("pdf")) {
    try {
      const snippet = await blob.slice(0, 256).text();
      const trimmed = snippet.trim().toLowerCase();
      if (!trimmed) return false;
      return trimmed.startsWith("<!doctype") || trimmed.startsWith("<html");
    } catch {
      return false;
    }
  }
  if (!type || type === "application/octet-stream") {
    try {
      const snippet = await blob.slice(0, 256).text();
      const trimmed = snippet.trim().toLowerCase();
      if (!trimmed) return false;
      return trimmed.startsWith("<!doctype") || trimmed.startsWith("<html");
    } catch {
      return false;
    }
  }
  return false;
};

const extractErrorMessages = (err: any): string[] => {
  const detail = err?.response?.data?.detail ?? err?.response?.data?.message ?? err?.message ?? err;
  const normalize = (value: any): string => {
    if (!value) return "Error";
    if (typeof value === "string") return value;
    const field = value.field || value.path || value.loc?.join?.(".");
    const msg = value.msg || value.message || value.error;
    return field && msg ? `${field}: ${msg}` : String(msg ?? value);
  };
  if (Array.isArray(detail)) return detail.map(normalize);
  if (typeof detail === "object") return [normalize(detail)];
  return [String(detail)];
};

type Props = {
  candidateId: string;
  ownerContext?: Record<string, any>;
  onFieldsApplied?: (doc: Document, fields: Record<string, any>) => void;
};

export default function CandidateDocuments({ candidateId, ownerContext, onFieldsApplied }: Props) {
  const { can } = usePermissions();
  const { t, locale } = useI18n();
  const translateStatus = useCallback(
    (status: DocumentStatus | string) =>
      t(DOCUMENT_STATUS_META[status as DocumentStatus]?.labelKey ?? status, { defaultValue: status }),
    [t],
  );
  const translateReadiness = useCallback(
    (state?: string) =>
      state ? t(READINESS_STATE_META[state]?.labelKey ?? state, { defaultValue: state }) : undefined,
    [t],
  );
  const translateKind = useCallback((kind: DocumentKind) => t(KIND_LABEL_KEYS[kind], { defaultValue: kind }), [t]);
  const translateRequestedFrom = useCallback(
    (value: DocumentRequestedFrom | undefined) =>
      value ? t(REQUESTED_FROM_LABEL_KEYS[value], { defaultValue: value }) : null,
    [t],
  );
  const translateProcess = useCallback(
    (value: DocumentProcessType | undefined | null) =>
      value ? t(PROCESS_LABEL_KEYS[value], { defaultValue: value }) : null,
    [t],
  );
  const canManageDocuments = can("documents.manage");

  const coreFromDocument = useCallback((doc: Document): CoreFields => ({
    number: doc.number ?? "",
    issue_date: doc.issue_date ?? doc.issued_at ?? "",
    expire_date: doc.expire_date ?? doc.expires_at ?? "",
    ordered_at: doc.ordered_at ?? "",
    valid_from: doc.valid_from ?? "",
    reminder_days_before:
      typeof doc.reminder_days_before === "number" ? doc.reminder_days_before : 30,
    requested_from: doc.requested_from,
    owner_id: doc.owner_id ?? "",
    comment: typeof doc.meta_json?.comment === "string" ? doc.meta_json.comment : "",
  }), []);

  const [docTypes, setDocTypes] = useState<DocType[]>([]);
  const [docs, setDocs] = useState<Document[]>([]);
  const [summaryResponse, setSummaryResponse] = useState<CandidateDocumentsSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const [selectedType, setSelectedType] = useState<string>("");
  const [customName, setCustomName] = useState("");
  const [customKind, setCustomKind] = useState<DocumentKind>("driver");
  const [customRequester, setCustomRequester] = useState<DocumentRequestedFrom>("driver");
  const [customProcessType, setCustomProcessType] = useState<DocumentProcessType>("other");
  const [title, setTitle] = useState("");
  const [additionalDescription, setAdditionalDescription] = useState("");
  const [additionalComment, setAdditionalComment] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);
  const [creationStatus, setCreationStatus] = useState<DocumentStatus>("requested");
  const [creationOrderedAt, setCreationOrderedAt] = useState<string>(() => computeTodayIso());
  const [creationValidFrom, setCreationValidFrom] = useState<string>("");
  const [creationReminderDays, setCreationReminderDays] = useState<string>("");
  const [creationMetadata, setCreationMetadata] = useState<MetadataState>({});
  const [creatingDocument, setCreatingDocument] = useState(false);

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContentType, setPreviewContentType] = useState<string | null>(null);

  const [kindFilter, setKindFilter] = useState<DocumentKind | "all">("all");
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [orderedFilter, setOrderedFilter] = useState<"all" | "ordered" | "not_ordered">("all");

  const [coreEdits, setCoreEdits] = useState<Record<string, CoreFields>>({});
  const [replaceFile, setReplaceFile] = useState<Record<string, File | null>>({});
  const [replaceUploading, setReplaceUploading] = useState<Record<string, boolean>>({});
  const [replacePct, setReplacePct] = useState<Record<string, number>>({});
  const [statusUpdating, setStatusUpdating] = useState<Record<string, boolean>>({});
  const [coreSaving, setCoreSaving] = useState<Record<string, boolean>>({});
  const [metadataEdits, setMetadataEdits] = useState<Record<string, MetadataState>>({});
  const [expandedDocs, setExpandedDocs] = useState<Record<string, boolean>>({});
  const [orderDrafts, setOrderDrafts] = useState<Record<string, OrderDraft>>({});
  const [orderingTypes, setOrderingTypes] = useState<Record<string, boolean>>({});
  const [expiringSoonOnly, setExpiringSoonOnly] = useState(false);
  const [passportIncompleteOnly, setPassportIncompleteOnly] = useState(false);

  const typeByCode = useMemo(() => new Map(docTypes.map((t) => [t.code, t])), [docTypes]);
  const selectedDocDefinition = useMemo(() => {
    if (!selectedType) return null;
    return typeByCode.get(selectedType) ?? null;
  }, [selectedType, typeByCode]);
  const selectedRequiredFiles = selectedDocDefinition?.required_files ?? null;
  const metadataRequiredFields = useMemo(() => {
    const schema =
      (selectedDocDefinition?.meta_schema as { required?: unknown }) ??
      (selectedDocDefinition?.metadata_schema as { required?: unknown });
    if (!schema || !Array.isArray(schema.required)) return [];
    return schema.required.map((field) => String(field));
  }, [selectedDocDefinition]);
  const buildFieldMap = useCallback((list: DocType[]) => {
    const map = new Map<string, MetadataFieldConfig[]>();
    list.forEach((type) => {
      const schema = type.metadata_schema ?? type.meta_schema ?? null;
      map.set(type.code, extractMetadataFields(schema));
    });
    return map;
  }, []);
  const metadataFieldMap = useMemo(() => buildFieldMap(docTypes), [docTypes, buildFieldMap]);
  const creationMetadataFields = useMemo(
    () => metadataFieldMap.get(selectedType ?? "") ?? [],
    [metadataFieldMap, selectedType]
  );

  useEffect(() => {
    if (!selectedType) {
      setCreationMetadata({});
      return;
    }
    setCreationMetadata(buildMetadataDefaults(creationMetadataFields));
  }, [selectedType, creationMetadataFields]);
  const scannerRequirements = useMemo(() => {
    if (!selectedRequiredFiles) return null;
    const cfg = selectedRequiredFiles as Record<string, any>;
    const accept = Array.isArray(cfg.accept) ? cfg.accept.join(", ") : undefined;
    const sizeLimit = cfg.max_total_mb
      ? t("admin.documents.scanner.max_total", { values: { mb: cfg.max_total_mb } })
      : undefined;
    const perPage = cfg.max_page_size_mb
      ? t("admin.documents.scanner.max_per_page", { values: { mb: cfg.max_page_size_mb } })
      : undefined;
    const frame = cfg.frame?.preset
      ? t("admin.documents.scanner.frame", { values: { preset: cfg.frame.preset } })
      : undefined;
    const formats = accept
      ? t("admin.documents.scanner.accept_formats", { values: { formats: accept } })
      : undefined;
    const common = [frame, formats, perPage, sizeLimit].filter(Boolean) as string[];
    if (cfg.type === "sides") {
      return {
        title: t("admin.documents.scanner.sides_title"),
        details: [
          cfg.sides && Array.isArray(cfg.sides)
            ? t("admin.documents.scanner.sides_order", { values: { order: cfg.sides.join(" → ") } })
            : undefined,
          cfg.sequence_required ? t("admin.documents.scanner.sequence_required") : undefined,
          ...common,
        ].filter(Boolean) as string[],
      };
    }
    if (cfg.type === "paged") {
      return {
        title: t("admin.documents.scanner.paged_title"),
        details: [
          cfg.min_pages ? t("admin.documents.scanner.min_pages", { values: { count: cfg.min_pages } }) : undefined,
          cfg.sequence_required ? t("admin.documents.scanner.sequence_required") : undefined,
          ...common,
        ].filter(Boolean) as string[],
      };
    }
    return {
      title: t("admin.documents.scanner.upload_title"),
      details: [
        cfg.min_files ? t("admin.documents.scanner.min_files", { values: { count: cfg.min_files } }) : undefined,
        cfg.max_files ? t("admin.documents.scanner.max_files", { values: { count: cfg.max_files } }) : undefined,
        ...common,
      ].filter(Boolean) as string[],
    };
  }, [selectedRequiredFiles, t]);
  const titleIsRequired =
    metadataRequiredFields.includes("title") || selectedType === "additional_document";

  const flash = (message: string) => {
    setInfo(message);
    window.setTimeout(() => setInfo(null), 2500);
  };

  const loadAll = useCallback(async () => {
    if (!candidateId) return;
    setLoading(true);
    setError(null);
    try {
      const orderedParam =
        orderedFilter === "ordered" ? true : orderedFilter === "not_ordered" ? false : undefined;
      const [typesResp, summaryResp, docsResp] = await Promise.all([
        getDocumentTypes(),
        getSummary(candidateId, { context: ownerContext ?? undefined, fillMissing: true }),
        listDocuments({ candidateId, ordered: orderedParam }),
      ]);
      const types = toArray<DocType>(typesResp);
      const localFieldMap = buildFieldMap(types);
      setDocTypes(types);
      setSummaryResponse(summaryResp);
      const summaryDocs = Array.isArray(summaryResp?.documents)
        ? (summaryResp.documents as Document[])
        : [];
      const docsList = Array.isArray(docsResp) ? docsResp : [];
      setDocs(docsList);

      const coreInitial: Record<string, CoreFields> = {};
      const metadataInitial: Record<string, MetadataState> = {};
      docsList.forEach((doc) => {
        coreInitial[doc.id] = coreFromDocument(doc);
        metadataInitial[doc.id] = buildMetadataStateFromDoc(doc, localFieldMap.get(doc.doc_type) ?? []);
      });
      setCoreEdits(coreInitial);
      setMetadataEdits(metadataInitial);

      const defaultType = (() => {
        if (!types.length) return "";
        const readyCodes = new Set(
          summaryDocs
            .filter((doc) => READY_STATUSES.has(doc.status))
            .map((doc) => doc.type_code)
        );
        const firstRequired = types.find((t) => t.required && !readyCodes.has(t.code));
        return firstRequired?.code || types[0].code;
      })();
      setSelectedType((prev) => prev || defaultType);
    } catch (e: any) {
      const fallback = t("admin.documents.errors.load_failed");
      const message = e?.response?.data?.detail || e?.message || fallback;
      setError(String(message));
    } finally {
      setLoading(false);
    }
  }, [candidateId, ownerContext, orderedFilter, coreFromDocument]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    const handler = (event: ClipboardEvent) => {
      if (!canManageDocuments) return;
      const item = Array.from(event.clipboardData?.items || []).find((i) => i.kind === "file");
      if (!item) return;
      const blob = item.getAsFile();
      if (!blob) return;
      if (isTooLarge(blob)) {
        setError(t("admin.documents.errors.file_too_large", { values: { limit: MAX_FILE_MB } }));
        return;
      }
      setFile(blob);
    };
    window.addEventListener("paste", handler);
    return () => window.removeEventListener("paste", handler);
  }, [canManageDocuments]);

useEffect(() => {
  setAdditionalDescription("");
  setAdditionalComment("");
}, [selectedType]);

  const isExpiringSoonDoc = useCallback(
    (doc: Document) => {
      const expiry = doc.expire_date || doc.expires_at;
      const diff = daysUntil(expiry);
      return diff !== null && diff >= 0 && diff <= EXPIRING_SOON_THRESHOLD_DAYS;
    },
    []
  );

  const isPassportIncompleteDoc = useCallback(
    (doc: Document) => doc.doc_type === "passport" && !READY_STATUSES.has(primaryStatus(doc)),
    []
  );

  const expiringSoonSet = useMemo(
    () => new Set(docs.filter((doc) => isExpiringSoonDoc(doc)).map((doc) => doc.id)),
    [docs, isExpiringSoonDoc]
  );

  const passportIncompleteSet = useMemo(
    () => new Set(docs.filter((doc) => isPassportIncompleteDoc(doc)).map((doc) => doc.id)),
    [docs, isPassportIncompleteDoc]
  );

  const groupedDocs = useMemo(() => {
    const search = searchQuery.trim().toLowerCase();
    const groups: Record<DocumentKind, Document[]> = { driver: [], employer: [], process: [] };

    docs.forEach((doc) => {
      if (kindFilter !== "all" && doc.kind !== kindFilter) return;
      const statusValue = primaryStatus(doc);
      if (statusFilter !== "all" && statusValue !== statusFilter) return;
      if (search) {
        const typeName =
          (typeByCode.get(doc.doc_type)?.name || typeByCode.get(doc.type_code)?.name || doc.doc_type).toLowerCase();
        const title = (doc.title || doc.custom_name || "").toLowerCase();
        if (!typeName.includes(search) && !title.includes(search) && !doc.doc_type.toLowerCase().includes(search)) {
          return;
        }
      }
      if (expiringSoonOnly && !expiringSoonSet.has(doc.id)) return;
      if (passportIncompleteOnly && !passportIncompleteSet.has(doc.id)) return;
      groups[doc.kind].push(doc);
    });

    KIND_ORDER.forEach((kind) => {
      groups[kind].sort((a, b) => {
        const statusA = primaryStatus(a);
        const statusB = primaryStatus(b);
        const rankA =
          DOCUMENT_STATUS_META[statusA]?.order ?? (typeof a.status_rank === "number" ? a.status_rank : 0);
        const rankB =
          DOCUMENT_STATUS_META[statusB]?.order ?? (typeof b.status_rank === "number" ? b.status_rank : 0);
        if (rankA !== rankB) return rankB - rankA;
        const orderedDiff = dateValue(b.ordered_at ?? null) - dateValue(a.ordered_at ?? null);
        if (orderedDiff !== 0) return orderedDiff;
        const expiresDiff =
          dateValue(a.expire_date ?? a.expires_at ?? null) - dateValue(b.expire_date ?? b.expires_at ?? null);
        if (expiresDiff !== 0) return expiresDiff;
        return (a.title || a.custom_name || a.doc_type).localeCompare(
          b.title || b.custom_name || b.doc_type,
          locale || undefined
        );
      });
    });

    return groups;
  }, [
    docs,
    kindFilter,
    statusFilter,
    searchQuery,
    typeByCode,
    expiringSoonOnly,
    passportIncompleteOnly,
    expiringSoonSet,
    passportIncompleteSet,
  ]);

  const statsByKind = useMemo(() => {
    const base: Record<DocumentKind, { total: number; ready: number; attention: number; negative: number; missing: number }> = {
      driver: { total: 0, ready: 0, attention: 0, negative: 0, missing: 0 },
      employer: { total: 0, ready: 0, attention: 0, negative: 0, missing: 0 },
      process: { total: 0, ready: 0, attention: 0, negative: 0, missing: 0 },
    };

    docs.forEach((doc) => {
      const bucket = base[doc.kind];
      bucket.total += 1;
      const statusValue = primaryStatus(doc);
      if (READY_STATUSES.has(statusValue)) bucket.ready += 1;
      else if (NEGATIVE_STATUSES.has(statusValue)) bucket.negative += 1;
      else if (statusValue === "missing") bucket.missing += 1;
      else bucket.attention += 1;
    });

    return base;
  }, [docs]);

  useEffect(() => {
    setOrderDrafts((prev) => {
      let changed = false;
      const next = { ...prev };
      docTypes.forEach((type) => {
        if (!type.orderable) return;
        if (!next[type.code]) {
          next[type.code] = defaultOrderDraft(type.code);
          changed = true;
        }
      });
      return changed ? next : prev;
    });
  }, [docTypes]);

  const checklist = summaryResponse?.checklist ?? summaryResponse?.summary?.checklist ?? null;

  const orderDraftForType = useCallback(
    (typeCode: string): OrderDraft => orderDrafts[typeCode] ?? defaultOrderDraft(typeCode),
    [orderDrafts]
  );

  const updateOrderDraftField = useCallback(
    (typeCode: string, field: keyof OrderDraft, value: string) => {
      setOrderDrafts((prev) => ({
        ...prev,
        [typeCode]: {
          ...(prev[typeCode] ?? defaultOrderDraft(typeCode)),
          [field]: value,
        },
      }));
    },
    []
  );

  const filteredCount = KIND_ORDER.reduce((acc, kind) => acc + (groupedDocs[kind]?.length ?? 0), 0);

  const updateDocumentState = useCallback((updated: Document) => {
    setDocs((prev) => {
      const found = prev.some((doc) => doc.id === updated.id);
      return found ? prev.map((doc) => (doc.id === updated.id ? updated : doc)) : [...prev, updated];
    });
    setSummaryResponse((prev) => {
      if (!prev) return prev;
      const exists = prev.documents.some((doc) => doc.id === updated.id);
      const documents = exists ? prev.documents.map((doc) => (doc.id === updated.id ? updated : doc)) : [...prev.documents, updated];
      return { ...prev, documents };
    });

    setCoreEdits((prev) => ({
      ...prev,
      [updated.id]: coreFromDocument(updated),
    }));
    setMetadataEdits((prev) => ({
      ...prev,
      [updated.id]: buildMetadataStateFromDoc(updated, metadataFieldMap.get(updated.doc_type) ?? []),
    }));
  }, [coreFromDocument, metadataFieldMap]);

  const summary = useMemo(() => {
    if (!summaryResponse) return null;
    const base = summaryResponse.summary;
    const checklist = summaryResponse.checklist ?? base.checklist ?? null;
    const requiredTypes: string[] = Array.isArray(checklist?.requiredTypes)
      ? checklist!.requiredTypes.map((t: any) => String(t))
      : [];
    if (!requiredTypes.length) return base;

    const coverageMap = new Map<string, Set<string>>();
    const addCoverage = (type: string, covered: string) => {
      if (!coverageMap.has(type)) coverageMap.set(type, new Set<string>());
      coverageMap.get(type)!.add(covered);
    };
    EQUIVALENT_TYPE_GROUPS.forEach((group) => {
      group.forEach((type) => {
        group.forEach((covered) => addCoverage(type, covered));
      });
    });

    const readyTypes = new Set<string>();
    const inProgressTypes = new Set<string>();
    const problemTypes = new Set<string>();

    docs.forEach((doc) => {
      const statusValue = primaryStatus(doc);
      const coverage = new Set<string>([doc.type_code]);
      const extra = coverageMap.get(doc.type_code);
      if (extra) extra.forEach((c) => coverage.add(c));
      coverage.forEach((type) => {
        if (READY_STATUSES.has(statusValue)) readyTypes.add(type);
        else if (NEGATIVE_STATUSES.has(statusValue)) problemTypes.add(type);
        else inProgressTypes.add(type);
      });
    });

    const missingTypes: string[] = [];
    const finalReady: string[] = [];
    const finalInProgress: string[] = [];
    const finalProblem: string[] = [];

    requiredTypes.forEach((type) => {
      if (readyTypes.has(type)) finalReady.push(type);
      else if (problemTypes.has(type)) finalProblem.push(type);
      else if (inProgressTypes.has(type)) finalInProgress.push(type);
      else missingTypes.push(type);
    });

    const total = requiredTypes.length;
    const ready = finalReady.length;
    const inProgress = finalInProgress.length;
    const problems = finalProblem.length;
    const missing = missingTypes.length;
    const percentReady = total === 0 ? 100 : Math.round((ready / total) * 100);

    return {
      ...base,
      percent_ready: percentReady,
      required: {
        ...base.required,
        ready,
        total,
        in_progress: inProgress,
        problems,
        problematic: finalProblem,
        missing: missingTypes,
        ready_types: finalReady,
        in_progress_types: finalInProgress,
        missing_count: missing,
      },
    };
  }, [summaryResponse, docs]);

  const requiredEntries = useMemo(() => {
    if (!checklist) return [] as Array<{ type: string; label: string; status: RequiredState; documents: Document[] }>;
    const reqSummary = summary?.required;
    const readySet = new Set(reqSummary?.ready_types ?? []);
    const inProgressSet = new Set(reqSummary?.in_progress_types ?? []);
    const problemSet = new Set(reqSummary?.problematic ?? []);
    const missingSet = new Set(reqSummary?.missing ?? []);

    return checklist.requiredTypes.map((rawType) => {
      const typeCode = String(rawType);
      let status: RequiredState = "missing";
      if (readySet.has(typeCode)) status = "ready";
      else if (problemSet.has(typeCode)) status = "problem";
      else if (inProgressSet.has(typeCode)) status = "in_progress";
      else if (missingSet.has(typeCode)) status = "missing";
      const label = typeByCode.get(typeCode)?.name || typeCode;
      const documentsForType = docs.filter((doc) => doc.type_code === typeCode);
      return { type: typeCode, label, status, documents: documentsForType };
    });
  }, [checklist, summary, docs, typeByCode]);


  const handleOrderType = useCallback(
    async (typeCode: string) => {
      if (!canManageDocuments || !candidateId) return;
      const typeInfo = typeByCode.get(typeCode);
      if (!typeInfo?.orderable) return;
      const draft = orderDraftForType(typeCode);
      if (!draft.ordered_at) {
        setError(t("admin.documents.errors.order_date_required"));
        updateOrderDraftField(typeCode, "ordered_at", computeTodayIso());
        return;
      }
      if (typeCode === "work_permit" && !draft.requested_from) {
        setError(t("admin.documents.errors.order_valid_from_required"));
        return;
      }
      setOrderingTypes((prev) => ({ ...prev, [typeCode]: true }));
      try {
        const payload: DocumentOrderInput = {
          candidate_id: candidateId,
          doc_type: typeCode,
          ordered_at: draft.ordered_at || undefined,
        };
        if (typeCode === "work_permit") {
          payload.requested_from = draft.requested_from ?? undefined;
        }
        if (ownerContext && Object.keys(ownerContext).length > 0) {
          payload.owner_context = ownerContext;
        }
        const orderedDoc = await orderDocument(payload);
        updateDocumentState(orderedDoc);
        flash(
          t("admin.documents.notifications.order_success", {
            values: { name: typeInfo?.name || typeCode },
          }),
        );
        await loadAll();
      } catch (e: any) {
        const message = extractErrorMessages(e)[0] || t("admin.documents.notifications.order_failed");
        setError(message);
      } finally {
        setOrderingTypes((prev) => ({ ...prev, [typeCode]: false }));
      }
    },
    [canManageDocuments, candidateId, ownerContext, orderDraftForType, typeByCode, updateDocumentState, loadAll, flash, updateOrderDraftField]
  );


  const resetCreationForm = () => {
    setFile(null);
    setTitle("");
    setAdditionalDescription("");
    setAdditionalComment("");
    setCustomName("");
    setCustomKind("driver");
    setCustomRequester("driver");
    setCustomProcessType("other");
    setCreationStatus("requested");
    setCreationOrderedAt(computeTodayIso());
    setCreationValidFrom("");
    setCreationReminderDays("");
    setCreationMetadata(buildMetadataDefaults(creationMetadataFields));
  };

  const buildCreatePayload = (overrides: Partial<CreateCandidateDocumentPayload> = {}) => {
    if (!selectedType) {
      throw new Error(t("admin.documents.errors.type_missing"));
    }
    const { meta_json: overridesMeta, ...restOverrides } = overrides;
    const base: CreateCandidateDocumentPayload = {
      owner_id: candidateId,
      doc_type: selectedType,
      status: creationStatus,
    };

    const orderedValue =
      overrides.ordered_at !== undefined ? overrides.ordered_at : creationOrderedAt.trim();
    if (orderedValue) {
      base.ordered_at = orderedValue;
    }

    const validValue =
      overrides.valid_from !== undefined ? overrides.valid_from : creationValidFrom.trim();
    if (validValue) {
      base.valid_from = validValue;
    }

    if (overrides.reminder_days_before !== undefined) {
      base.reminder_days_before = overrides.reminder_days_before;
    } else if (creationReminderDays.trim()) {
      const parsed = Number.parseInt(creationReminderDays, 10);
      if (!Number.isNaN(parsed)) {
        base.reminder_days_before = parsed;
      }
    }

    if (selectedType === "other") {
      const trimmedName = customName.trim();
      if (trimmedName) {
        base.custom_name = trimmedName;
      }
      base.kind = customKind;
      base.requested_from = customRequester;
      base.process_type = customKind === "process" ? customProcessType : "other";
    }

    const metaPayload: Record<string, any> = {};
    const trimmedTitle = title.trim();

    if (selectedType === "additional_document") {
      if (!trimmedTitle) {
        throw new Error(t("admin.documents.errors.custom_name_missing"));
      }
      const desc = additionalDescription.trim();
      if (!desc) {
        throw new Error(t("admin.documents.errors.description_missing"));
      }
      const commentValue = additionalComment.trim();
      if (!commentValue) {
        throw new Error(t("admin.documents.errors.comment_missing"));
      }
      base.title = trimmedTitle;
      metaPayload.title = trimmedTitle;
      metaPayload.description = desc;
      metaPayload.comment = commentValue;
    } else if (trimmedTitle) {
      base.title = trimmedTitle;
    }

    const merged: CreateCandidateDocumentPayload = { ...base, ...restOverrides };
    const metaFields = metadataFieldMap.get(selectedType) ?? [];
    const normalizedMeta = buildMetadataPayloadFromState(metaFields, creationMetadata);
    if (metaFields.length > 0) {
      metaFields.forEach((field) => {
        if (field.required) {
          const value = normalizedMeta[field.name];
          const isEmpty =
            value === null ||
            value === undefined ||
            value === "" ||
            (Array.isArray(value) && value.length === 0);
          if (isEmpty) {
            throw new Error(
              t("admin.documents.errors.metadata_missing", {
                values: {
                  field: t(`${METADATA_LABEL_NS}.${field.name}`, { defaultValue: field.name }),
                },
              })
            );
          }
        }
      });
    }
    const combinedMeta = { ...(overridesMeta ?? {}), ...metaPayload, ...normalizedMeta };
    if (Object.keys(combinedMeta).length > 0) {
      merged.meta_json = combinedMeta;
    }
    return merged;
  };

  const doUpload = async () => {
    if (!canManageDocuments) {
      setError(t("admin.documents.errors.permission_upload"));
      return;
    }
    if (!candidateId || !selectedType) return;
    if (selectedType === "other" && !customName.trim()) {
      setError(t("admin.documents.errors.custom_name_missing"));
      return;
    }
    if (!file) {
      setError(t("admin.documents.errors.file_missing"));
      return;
    }
    if (isTooLarge(file)) {
      setError(t("admin.documents.errors.file_too_large", { values: { limit: MAX_FILE_MB } }));
      return;
    }

    let payload: CreateCandidateDocumentPayload;
    try {
      payload = buildCreatePayload();
    } catch (validationError: any) {
      setError(validationError?.message || t("admin.documents.errors.fields_missing"));
      return;
    }
    setUploading(true);
    setUploadPct(0);
    setError(null);
    let timer: number | undefined;
    try {
      const created = await createCandidateDocument(payload);
      updateDocumentState(created);
      if (onFieldsApplied) {
        onFieldsApplied(created, created.meta_json ?? {});
      }

      const presign = await presignUpload(created.id);
      const key = presign?.fields?.key || presign?.key || `documents/${created.id}/original.bin`;
      timer = window.setInterval(() => {
        setUploadPct((prev) => Math.min(90, prev + 5));
      }, 150) as unknown as number;
      await mockUpload({ key, file });
      if (timer) window.clearInterval(timer);
      setUploadPct(100);

      resetCreationForm();
      setExpandedDocs((prev) => ({ ...prev, [created.id]: true }));
      await loadAll();
      flash(t("admin.documents.notifications.upload_success"));
    } catch (e: any) {
      if (timer) window.clearInterval(timer);
      setUploadPct(0);
      const message =
        e?.response?.data?.detail || e?.message || t("admin.documents.notifications.upload_failed");
      setError(String(message));
    } finally {
      setUploading(false);
      window.setTimeout(() => setUploadPct(0), 400);
    }
  };

  const createDocumentWithoutFile = async () => {
    if (!canManageDocuments) {
      setError(t("admin.documents.errors.permission_create"));
      return;
    }
    if (!candidateId || !selectedType) return;
    if (selectedType === "other" && !customName.trim()) {
      setError(t("admin.documents.errors.custom_name_missing"));
      return;
    }

    let payload: CreateCandidateDocumentPayload;
    const statusAtCreation = creationStatus;
    try {
      payload = buildCreatePayload();
    } catch (validationError: any) {
      setError(validationError?.message || t("admin.documents.errors.fields_missing"));
      return;
    }

    setCreatingDocument(true);
    setError(null);
    try {
      const created = await createCandidateDocument(payload);
      updateDocumentState(created);
      if (onFieldsApplied) {
        onFieldsApplied(created, created.meta_json ?? {});
      }
      resetCreationForm();
      setExpandedDocs((prev) => ({ ...prev, [created.id]: true }));
      await loadAll();
      flash(
        statusAtCreation === "requested"
          ? t("admin.documents.notifications.order_created")
          : t("admin.documents.notifications.create_success"),
      );
    } catch (e: any) {
      const message = e?.response?.data?.detail || e?.message || t("admin.documents.notifications.create_failed");
      setError(String(message));
    } finally {
      setCreatingDocument(false);
    }
  };

  const doDelete = async (docId: string) => {
    if (!canManageDocuments) {
      setError(t("admin.documents.errors.permission_delete"));
      return;
    }
    setError(null);
    try {
      await deleteDocument(docId);
      flash(t("admin.documents.notifications.delete_success"));
      await loadAll();
    } catch (e: any) {
      const message =
        e?.response?.data?.detail || e?.message || t("admin.documents.notifications.delete_failed");
      setError(String(message));
    }
  };

  const updateStatus = async (doc: Document, newStatus: DocumentStatus) => {
    if (!canManageDocuments) {
      setError(t("admin.documents.errors.permission_status"));
      return;
    }
    setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
    try {
      const updated = await patchDocument(doc.id, { status: newStatus } as DocumentPatchPayload);
      updateDocumentState(updated);
      flash(t("admin.documents.notifications.status_updated"));
      await loadAll();
    } catch (e: any) {
      const messages = extractErrorMessages(e);
      setError(messages[0] || t("admin.documents.notifications.status_failed"));
    } finally {
      setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
    }
  };

  const approveDocument = async (doc: Document) => {
    if (!canManageDocuments) {
      setError(t("admin.documents.errors.permission_approve"));
      return;
    }
    setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
    try {
      const updated = await checkDocument(doc.id, { decision: "approved" });
      updateDocumentState(updated);
      flash(t("admin.documents.notifications.approve_success"));
      await loadAll();
    } catch (e: any) {
      const messages = extractErrorMessages(e);
      setError(messages[0] || t("admin.documents.notifications.approve_failed"));
    } finally {
      setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
    }
  };

  const createDocumentFromChecklist = async (doc: Document) => {
    if (!canManageDocuments) {
      setError(t("admin.documents.errors.permission_create"));
      return;
    }
    if (!candidateId) return;
    setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
    try {
      const metaPayload = { ...(doc.meta_json ?? {}) };
      delete (metaPayload as any).synthetic;

      const created = await createCandidateDocument({
        owner_id: candidateId,
        doc_type: doc.type_code,
        kind: doc.kind,
        requested_from: doc.requested_from,
        process_type: doc.process_type,
        status: "requested",
        reminder_days_before: doc.reminder_days_before ?? 30,
        meta_json: metaPayload,
      });
      updateDocumentState(created);
      if (onFieldsApplied) {
        onFieldsApplied(created, created.meta_json ?? {});
      }
      flash(t("admin.documents.notifications.created_from_checklist"));
      await loadAll();
    } catch (e: any) {
      const messages = extractErrorMessages(e);
      setError(messages[0] || t("admin.documents.notifications.create_failed"));
    } finally {
      setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
    }
  };

  const startWorkflow = async (doc: Document) => {
    if (!canManageDocuments) {
      setError(t("admin.documents.errors.permission_workflow"));
      return;
    }
    const workflowSource = doc.workflow ? JSON.parse(JSON.stringify(doc.workflow)) : null;
    if (!workflowSource || !Array.isArray(workflowSource.steps) || !workflowSource.steps.length) {
      return;
    }
    const nowIso = new Date().toISOString();
    const steps = workflowSource.steps.map((step: any, index: number) => {
      const status = String(step.status || "").toLowerCase();
      if (status === "done") {
        return { ...step, status: "done" };
      }
      if (index === 0) {
        return {
          ...step,
          status: "in_progress",
          completed_at: step.completed_at ?? null,
          ordered_at: step.ordered_at ?? nowIso,
        };
      }
      return { ...step, status: "pending", completed_at: step.completed_at ?? null };
    });
    workflowSource.steps = steps;
    workflowSource.current_step = steps.find((step: any) => step.status !== "done")?.code ?? null;
    workflowSource.completed = !workflowSource.current_step;

    const payload: DocumentPatchPayload = {
      status: doc.status === "missing" ? "requested" : doc.status,
      workflow: workflowSource,
    };

    setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
    try {
      const updated = await patchDocument(doc.id, payload);
      updateDocumentState(updated);
      flash(t("admin.documents.notifications.workflow_started"));
      await loadAll();
    } catch (e: any) {
      const messages = extractErrorMessages(e);
      setError(messages[0] || t("admin.documents.notifications.workflow_failed"));
    } finally {
      setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
    }
  };

  const completeWorkflowStep = async (doc: Document, stepCode: string) => {
    if (!canManageDocuments) {
      setError(t("admin.documents.errors.permission_workflow"));
      return;
    }
    const workflowSource = doc.workflow ? JSON.parse(JSON.stringify(doc.workflow)) : null;
    if (!workflowSource || !Array.isArray(workflowSource.steps) || !workflowSource.steps.length) {
      return;
    }
    const nowIso = new Date().toISOString();
    let nextMarked = false;
    const steps = workflowSource.steps.map((step: any) => {
      const status = String(step.status || "").toLowerCase();
      if (step.code === stepCode) {
        return {
          ...step,
          status: "done",
          completed_at: step.completed_at ?? nowIso,
        };
      }
      if (status === "done") {
        return { ...step, status: "done" };
      }
      if (!nextMarked) {
        nextMarked = true;
        const dueInHours =
          typeof step.due_in_hours === "number" && Number.isFinite(step.due_in_hours)
            ? step.due_in_hours
            : null;
        const dueAt =
          step.due_at ??
          (dueInHours != null
            ? new Date(Date.now() + dueInHours * 60 * 60 * 1000).toISOString()
            : null);
        return {
          ...step,
          status: "in_progress",
          completed_at: null,
          ordered_at: step.ordered_at ?? nowIso,
          due_at: dueAt,
        };
      }
      return { ...step, status: "pending", completed_at: null };
    });

    workflowSource.steps = steps;
    workflowSource.current_step = steps.find((step: any) => step.status !== "done")?.code ?? null;
    workflowSource.completed = !workflowSource.current_step;

    setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
    try {
      const updated = await patchDocument(doc.id, { workflow: workflowSource });
      updateDocumentState(updated);
      flash(t("admin.documents.notifications.workflow_step_marked"));
      await loadAll();
    } catch (e: any) {
      const messages = extractErrorMessages(e);
      setError(messages[0] || t("admin.documents.notifications.workflow_failed"));
    } finally {
      setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
    }
  };

  const saveCoreFields = async (doc: Document) => {
    if (!canManageDocuments) {
      setError(t("admin.documents.errors.permission_edit"));
      return;
    }
    const edits = coreEdits[doc.id] ?? {};
    const payload: DocumentPatchPayload = {};

    if (edits.number !== undefined) {
      payload.number = edits.number && edits.number.trim() ? edits.number.trim() : null;
    }
    if (edits.issue_date !== undefined) {
      payload.issue_date = edits.issue_date ? String(edits.issue_date).slice(0, 10) : null;
    }
    if (edits.expire_date !== undefined) {
      payload.expire_date = edits.expire_date ? String(edits.expire_date).slice(0, 10) : null;
    }
    if (edits.ordered_at !== undefined) {
      payload.ordered_at = edits.ordered_at ? String(edits.ordered_at).slice(0, 10) : null;
    }
    if (edits.valid_from !== undefined) {
      payload.valid_from = edits.valid_from ? String(edits.valid_from).slice(0, 10) : null;
    }
    if (edits.reminder_days_before !== undefined) {
      payload.reminder_days_before = edits.reminder_days_before ?? null;
    }
    if (edits.requested_from) {
      payload.requested_from = edits.requested_from;
    }
    if (edits.owner_id !== undefined) {
      payload.owner_id = edits.owner_id && edits.owner_id.trim() ? edits.owner_id.trim() : null;
    }

    const baseMeta: Record<string, any> = { ...(doc.meta_json ?? {}) };
    let metaChanged = false;
    if (edits.comment !== undefined) {
      if (edits.comment && edits.comment.trim()) {
        baseMeta.comment = edits.comment.trim();
      } else {
        delete baseMeta.comment;
      }
      metaChanged = true;
    }

    const metaFields = metadataFieldMap.get(doc.doc_type) ?? [];
    if (metaFields.length > 0) {
      const current = buildMetadataPayloadFromState(metaFields, metadataEdits[doc.id]);
      metaFields.forEach((field) => {
        const nextValue = current[field.name];
        const prevValue = baseMeta[field.name];
        const isEmpty =
          nextValue === null ||
          nextValue === undefined ||
          nextValue === "" ||
          (Array.isArray(nextValue) && nextValue.length === 0);
        if (isEmpty) {
          if (prevValue !== undefined) {
            delete baseMeta[field.name];
            metaChanged = true;
          }
        } else if (JSON.stringify(prevValue) !== JSON.stringify(nextValue)) {
          baseMeta[field.name] = nextValue;
          metaChanged = true;
        }
      });
    }
    if (metaChanged) {
      payload.meta_json = baseMeta;
    }

    if (Object.keys(payload).length === 0) {
      return;
    }

    setCoreSaving((prev) => ({ ...prev, [doc.id]: true }));
    try {
      const updated = await patchDocument(doc.id, payload);
      updateDocumentState(updated);
      if (onFieldsApplied) {
        onFieldsApplied(updated, payload.meta_json ?? {});
      }
      flash(t("admin.documents.notifications.core_saved"));
      await loadAll();
    } catch (e: any) {
      const messages = extractErrorMessages(e);
      setError(messages[0] || t("admin.documents.notifications.core_failed"));
    } finally {
      setCoreSaving((prev) => ({ ...prev, [doc.id]: false }));
    }
  };

  const resetCoreFields = (doc: Document) => {
    setCoreEdits((prev) => ({
      ...prev,
      [doc.id]: coreFromDocument(doc),
    }));
    setMetadataEdits((prev) => ({
      ...prev,
      [doc.id]: buildMetadataStateFromDoc(doc, metadataFieldMap.get(doc.doc_type) ?? []),
    }));
  };

  const rejectDocument = async (doc: Document) => {
    if (!canManageDocuments) {
      setError(t("admin.documents.errors.permission_reject"));
      return;
    }
    const reason = window.prompt(t("admin.documents.prompts.reject_reason"), "") ?? undefined;
    setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
    try {
      const payload: { decision: "rejected"; comment?: string } = { decision: "rejected" };
      if (reason && reason.trim()) payload.comment = reason.trim();
      const updated = await checkDocument(doc.id, payload);
      updateDocumentState(updated);
      flash(t("admin.documents.notifications.reject_success"));
      await loadAll();
    } catch (e: any) {
      const messages = extractErrorMessages(e);
      setError(messages[0] || t("admin.documents.notifications.reject_failed"));
    } finally {
      setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
    }
  };

  const [previewRevoker, setPreviewRevoker] = useState<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      if (previewRevoker) previewRevoker();
    };
  }, [previewRevoker]);

  const openDoc = async (doc: Document) => {
    setError(null);
    if (previewRevoker) {
      previewRevoker();
      setPreviewRevoker(null);
    }
    setPreviewContentType(null);
    let directLink: string | null = null;
    let directFilename: string | null = null;
    try {
      try {
        const res = await getDocumentFileUrl(doc.id);
        const rawLink = typeof res === "string" ? res : res?.url;
        if (rawLink) {
          const resolved = resolveDocumentUrl(rawLink);
          if (resolved) {
            directLink = resolved;
            directFilename = filenameFromUrl(resolved);
          }
        }
      } catch (fetchLinkError: any) {
        if (fetchLinkError?.response?.status && fetchLinkError.response.status !== 404) {
          throw fetchLinkError;
        }
      }

      const fileData = await downloadDocumentFile(doc.id);
      const { blob, filename, contentType } = fileData;
      const previewable = guessPreviewable(contentType, filename);

      if (!blob || blob.size === 0) {
        if (directLink) {
          window.open(directLink, "_blank", "noopener");
          setPreviewUrl(null);
          setPreviewOpen(false);
          setPreviewContentType(null);
          return;
        }
        setError(t("admin.documents.errors.file_fetch_failed"));
        return;
      }

      const objectUrl = URL.createObjectURL(blob);
      const looksLikeHtml = await isProbablyHtmlBlob(blob, contentType);
      if (looksLikeHtml) {
        URL.revokeObjectURL(objectUrl);
        setPreviewRevoker(null);
        if (directLink) {
          window.open(directLink, "_blank", "noopener");
          return;
        }
        setError(t("admin.documents.errors.file_missing_remote"));
        return;
      }

      if (previewable) {
        if (previewRevoker) previewRevoker();
        const lowerType = (contentType || "").toLowerCase();
        const lowerFilename = (filename || "").toLowerCase();
        const isPdf = lowerType.includes("pdf") || lowerFilename.endsWith(".pdf");
        const previewMime = detectPreviewMime(contentType, filename);
        setPreviewUrl(objectUrl);
        setPreviewOpen(true);
        setPreviewContentType(previewMime ?? (isPdf ? "application/pdf" : "image/*"));
        setPreviewRevoker(() => () => {
          URL.revokeObjectURL(objectUrl);
        });
        return;
      }

      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = filename || doc.title || doc.custom_name || directFilename || "document";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(objectUrl);
      setPreviewRevoker(null);
    } catch (e: any) {
      const message =
        e?.response?.data?.detail || e?.message || t("admin.documents.errors.file_open_failed");
      setError(String(message));
      if (directLink) {
        window.open(directLink, "_blank", "noopener");
      }
    }
  };

  const renderWorkflow = (doc: Document) => {
    const workflow = doc.workflow as DocumentWorkflow | undefined;
    const steps = Array.isArray(workflow?.steps) ? workflow!.steps : [];
    if (!steps.length) return null;
    const completed = steps.filter((step) => String(step.status).toLowerCase() === "done").length;
    const total = steps.length;
    const progress = total > 0 ? Math.round((completed / total) * 100) : 0;
    const processLabel =
      translateProcess(workflow?.process_type ?? doc.process_type) ?? doc.process_type;
    const synthetic = Boolean((doc.meta_json as any)?.synthetic || (doc.meta as any)?.synthetic);
    const canModify = canManageDocuments && !synthetic;
    const hasActive = steps.some((step) => String(step.status || "").toLowerCase() === "in_progress");
    const unfinishedExists = steps.some((step) => String(step.status || "").toLowerCase() !== "done");
    const canStart = canModify && !hasActive && unfinishedExists;
    return (
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600">
          <span className="font-semibold text-gray-700">{t("admin.documents.workflow.title")}</span>
          <span>{processLabel}</span>
          <span className="ml-auto text-gray-500">{completed}/{total}</span>
          {canStart && (
            <button className="btn-primary btn-xs" onClick={() => startWorkflow(doc)}>
              {t("admin.documents.actions.order")}
            </button>
          )}
        </div>
        <div className="h-1.5 rounded bg-gray-200">
          <div className="h-full rounded bg-blue-500" style={{ width: `${progress}%` }} />
        </div>
        <div className="space-y-1">
          {steps.map((step: DocumentWorkflowStep) => {
            const rawStatus = String(step.status || "pending").toLowerCase();
            const isDone = rawStatus === "done";
            const badge = DOCUMENT_STATUS_META[step.status as DocumentStatus]?.color ?? "bg-gray-100 text-gray-600";
            const dueAtDate = step.due_at ? new Date(step.due_at) : null;
            const overdue = Boolean(dueAtDate && dueAtDate.getTime() < Date.now() && !isDone);
            return (
              <div key={step.code} className="rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-600">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-gray-700">{step.title || step.code}</span>
                  <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5", badge)}>
                    {translateStatus(step.status || rawStatus)}
                  </span>
                  {step.ordered_at && (
                    <span className="text-gray-500">
                      {t("admin.documents.workflow.ordered_at", {
                        values: { datetime: formatDateTime(step.ordered_at) ?? "" },
                      })}
                    </span>
                  )}
                  {step.due_at && (
                    <span className={clsx("text-gray-500", overdue && "text-rose-600 font-semibold")}>
                      {t("admin.documents.workflow.due_at", {
                        values: { datetime: formatDateTime(step.due_at) ?? "" },
                      })}
                    </span>
                  )}
                  {typeof step.due_in_hours === "number" && !Number.isNaN(step.due_in_hours) && (
                    <span className="text-gray-400">
                      {t("admin.documents.workflow.due_in_hours", { values: { hours: step.due_in_hours } })}
                    </span>
                  )}
                  {step.completed_at && (
                    <span className="text-gray-500">
                      {t("admin.documents.workflow.completed_at", {
                        values: { datetime: formatDateTime(step.completed_at) ?? "" },
                      })}
                    </span>
                  )}
                  {overdue && (
                    <span className="rounded bg-rose-100 px-2 py-0.5 text-rose-700">
                      {t("admin.documents.badges.overdue")}
                    </span>
                  )}
                  {canModify && !isDone && (
                    <button
                      className="btn-ghost btn-xs"
                      onClick={() => completeWorkflowStep(doc, step.code)}
                    >
                      {t("admin.documents.actions.mark_done")}
                    </button>
                  )}
                </div>
                {step.notes && <div className="mt-1 text-gray-500">{step.notes}</div>}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderReminders = (doc: Document) => {
    const reminders = Array.isArray(doc.reminders) ? doc.reminders : [];
    if (!reminders.length) return null;
    return (
      <div className="flex flex-wrap gap-2 text-[11px] text-gray-600">
        {reminders.slice(0, 5).map((reminder: DocumentReminder, idx) => (
          <span
            key={`${doc.id}-reminder-${idx}`}
            className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5"
          >
            ⏰ {reminder.step_code ? `${reminder.step_code}: ` : ""}{formatDate(reminder.due_at) || ""}
          </span>
        ))}
      </div>
    );
  };

  const renderLastCheck = (doc: Document) => {
    const check = doc.last_check as DocumentCheck | null | undefined;
    if (!check) return null;
    const badge = check.decision === "approved" ? "bg-green-50 text-green-700" : "bg-rose-50 text-rose-700";
    const decisionLabel =
      check.decision === "approved"
        ? t("admin.documents.badges.approved")
        : t("admin.documents.badges.rejected");
    return (
      <div className="rounded border border-gray-200 bg-white px-3 py-2 text-xs text-gray-600">
        <div className="flex flex-wrap items-center gap-2">
          <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5", badge)}>
            {decisionLabel}
          </span>
          {check.reviewer_id && (
            <span className="text-gray-500">
              {t("admin.documents.labels.reviewer", { values: { reviewer: check.reviewer_id } })}
            </span>
          )}
          {check.created_at && <span className="text-gray-500">{formatDateTime(check.created_at)}</span>}
        </div>
        {check.comment && <div className="mt-1 text-gray-600">{check.comment}</div>}
      </div>
    );
  };

  const renderMetadataFieldInput = (
    field: MetadataFieldConfig,
    value: any,
    onChange: (next: any) => void,
    disabled: boolean
  ) => {
    const label = t(`${METADATA_LABEL_NS}.${field.name}`, {
      defaultValue: field.name.replace(/_/g, " "),
    });
    const requiredMark = field.required ? "*" : "";
    if (field.input === "boolean") {
      return (
        <label className="flex items-center gap-2 text-xs text-gray-600">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-gray-300"
            checked={Boolean(value)}
            onChange={(e) => onChange(e.target.checked)}
            disabled={disabled}
          />
          <span className="text-[11px] font-medium uppercase text-gray-500">
            {label}
            {requiredMark && <span className="ml-0.5 text-rose-500">{requiredMark}</span>}
          </span>
        </label>
      );
    }
    if (field.input === "multiselect") {
      return (
        <div className="rounded border border-gray-200 p-2">
          <div className="text-[11px] font-semibold uppercase text-gray-500">
            {label}
            {requiredMark && <span className="ml-0.5 text-rose-500">{requiredMark}</span>}
          </div>
          <div className="mt-1 space-y-1">
            {(field.enumValues ?? []).map((option) => {
              const checked = Array.isArray(value) ? value.includes(option) : false;
              return (
                <label key={option} className="flex items-center gap-2 text-xs text-gray-600">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-gray-300"
                    checked={checked}
                    disabled={disabled}
                    onChange={(e) => {
                      const next = new Set(Array.isArray(value) ? value : []);
                      if (e.target.checked) next.add(option);
                      else next.delete(option);
                      onChange(Array.from(next));
                    }}
                  />
                  <span>{option}</span>
                </label>
              );
            })}
          </div>
        </div>
      );
    }
    if (field.input === "select") {
      return (
        <label className="block text-xs text-gray-600">
          <div className="text-[11px] font-semibold uppercase text-gray-500">
            {label}
            {requiredMark && <span className="ml-0.5 text-rose-500">{requiredMark}</span>}
          </div>
          <select
            className="input input-sm mt-1"
            value={value ?? ""}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          >
            <option value="">{t("admin.documents.forms.select_placeholder", { defaultValue: "Select" })}</option>
            {(field.enumValues ?? []).map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      );
    }
    if (field.input === "number") {
      return (
        <label className="block text-xs text-gray-600">
          <div className="text-[11px] font-semibold uppercase text-gray-500">
            {label}
            {requiredMark && <span className="ml-0.5 text-rose-500">{requiredMark}</span>}
          </div>
          <input
            className="input input-sm mt-1"
            type="number"
            value={value ?? ""}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          />
        </label>
      );
    }
    if (field.input === "date") {
      return (
        <label className="block text-xs text-gray-600">
          <div className="text-[11px] font-semibold uppercase text-gray-500">
            {label}
            {requiredMark && <span className="ml-0.5 text-rose-500">{requiredMark}</span>}
          </div>
          <input
            className="input input-sm mt-1"
            type="date"
            value={value ?? ""}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          />
        </label>
      );
    }
    return (
      <label className="block text-xs text-gray-600">
        <div className="text-[11px] font-semibold uppercase text-gray-500">
          {label}
          {requiredMark && <span className="ml-0.5 text-rose-500">{requiredMark}</span>}
        </div>
        <input
          className="input input-sm mt-1"
          type="text"
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        />
      </label>
    );
  };

  const renderDocumentCard = (doc: Document) => {
    const typeInfo = typeByCode.get(doc.doc_type) ?? typeByCode.get(doc.type_code);
    const typeLabel = typeInfo?.name || doc.doc_type;
    const title = doc.custom_name || doc.title || typeLabel;
    const statusValue = primaryStatus(doc);
    const statusMeta =
      DOCUMENT_STATUS_META[statusValue] ?? {
        labelKey: statusValue,
        color: "bg-gray-100 text-gray-600",
        order: 99,
      };
    const metadataFields = metadataFieldMap.get(doc.doc_type) ?? [];
    const metadataValues = metadataEdits[doc.id] ?? buildMetadataStateFromDoc(doc, metadataFields);
    const docDefinition = typeByCode.get(doc.doc_type) ?? typeByCode.get(doc.type_code);
    const isOrderableDoc = Boolean(docDefinition?.orderable);
    const statusLabel = translateStatus(statusValue);
    const selectStatus = statusValue;
    const synthetic = Boolean((doc.meta_json as any)?.synthetic || (doc.meta as any)?.synthetic);
    const requirementSources = Array.isArray((doc.meta_json as any)?.checklist_sources)
      ? (doc.meta_json as any).checklist_sources.map((item: any) => String(item))
      : [];
    const readinessState =
      READY_STATUSES.has(statusValue) || NEGATIVE_STATUSES.has(statusValue)
        ? ""
        : doc.readiness_state
        ? String(doc.readiness_state).toLowerCase()
        : "";
    const readinessMeta = readinessState ? READINESS_STATE_META[readinessState] : undefined;
    const readinessLabel = translateReadiness(readinessState);
    const hasFiles = doc.has_files ?? (Array.isArray(doc.files) && doc.files.length > 0);
    const core = coreEdits[doc.id] ?? coreFromDocument(doc);
    const requestedFromDate = resolveRequestedFromDate(doc);
    const isExpiringSoon = isExpiringSoonDoc(doc);
    const isPassportIncomplete = isPassportIncompleteDoc(doc);
    const updateCoreField = (field: keyof CoreFields, value: any) => {
      setCoreEdits((prev) => ({
        ...prev,
        [doc.id]: { ...(prev[doc.id] ?? core), [field]: value },
      }));
    };

    const expanded = Boolean(expandedDocs[doc.id]);
    const toggleExpanded = () => {
      setExpandedDocs((prev) => ({ ...prev, [doc.id]: !prev[doc.id] }));
    };

    const selectedReplaceFile = replaceFile[doc.id] ?? null;
    const uploadProgress = replacePct[doc.id] || 0;
    const isReplacing = Boolean(replaceUploading[doc.id]);

    const handleReplaceUpload = async () => {
      const nextFile = replaceFile[doc.id];
      if (!nextFile) return;
      setReplaceUploading((prev) => ({ ...prev, [doc.id]: true }));
      setReplacePct((prev) => ({ ...prev, [doc.id]: 0 }));
      const timer = window.setInterval(() => {
        setReplacePct((prev) => ({
          ...prev,
          [doc.id]: Math.min(90, (prev[doc.id] || 0) + 5),
        }));
      }, 150) as unknown as number;
      try {
        const presign = await presignUpload(doc.id);
        const key = presign?.fields?.key || presign?.key || `documents/${doc.id}/original.bin`;
        await mockUpload({ key, file: nextFile });
        window.clearInterval(timer);
        setReplacePct((prev) => ({ ...prev, [doc.id]: 100 }));
        await loadAll();
        flash(t("admin.documents.notifications.replace_success"));
        setReplaceFile((prev) => ({ ...prev, [doc.id]: null }));
      } catch (e: any) {
        window.clearInterval(timer);
        setReplacePct((prev) => ({ ...prev, [doc.id]: 0 }));
        const message =
          e?.response?.data?.detail || e?.message || t("admin.documents.notifications.replace_failed");
        setError(String(message));
      } finally {
        setReplaceUploading((prev) => ({ ...prev, [doc.id]: false }));
        window.setTimeout(() => {
          setReplacePct((prev) => ({ ...prev, [doc.id]: 0 }));
        }, 400);
      }
    };

    return (
      <div key={doc.id} className="rounded border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:gap-4">
          <button
            type="button"
            className="btn-ghost btn-xs self-start"
            onClick={toggleExpanded}
            aria-expanded={expanded}
            aria-label={
              expanded
                ? t('admin.documents.aria.collapse_document')
                : t('admin.documents.aria.expand_document')
            }
          >
            {expanded ? "▾" : "▸"}
          </button>
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-base font-semibold text-gray-800">{title}</span>
              <span
              className={clsx(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs",
                statusMeta.color
              )}
            >
                {statusLabel}
                {statusUpdating[doc.id] && <span className="text-[10px] text-gray-600">…</span>}
              </span>
              {readinessState && (
                <span
                  className={clsx(
                    "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs",
                    readinessMeta?.className ?? "bg-gray-100 text-gray-600"
                  )}
                >
                  {readinessLabel ?? doc.readiness_state}
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
              <span>{typeLabel}</span>
              <span>{translateRequestedFrom(doc.requested_from) ?? doc.requested_from}</span>
              {doc.process_type && doc.process_type !== "none" && (
                <span>{translateProcess(doc.process_type) ?? doc.process_type}</span>
              )}
              {doc.ordered_at && (
                <span>
                  {t('admin.documents.labels.ordered_at', { defaultValue: 'Ordered' })} {formatDate(doc.ordered_at)}
                </span>
              )}
              {requestedFromDate && (
                <span>
                  {t('admin.documents.labels.requested_from_date', { defaultValue: 'Requested from' })}{" "}
                  {formatDate(requestedFromDate)}
                </span>
              )}
              {doc.valid_from && (
                <span>
                  {t('admin.documents.labels.valid_from', { defaultValue: 'Valid from' })} {formatDate(doc.valid_from)}
                </span>
              )}
              <span
                className={clsx(
                  "inline-flex items-center gap-1 rounded-full px-2 py-0.5",
                  hasFiles ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-500"
                )}
              >
                {hasFiles ? t('admin.documents.badges.files_present') : t('admin.documents.badges.files_missing')}
              </span>
              {isExpiringSoon && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-amber-700">
                  {t('admin.documents.badges.expiring', { values: { days: EXPIRING_SOON_THRESHOLD_DAYS } })}
                </span>
              )}
              {isPassportIncomplete && (
                <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-rose-700">
                  {t('admin.documents.badges.passport_incomplete')}
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1 text-xs text-gray-500">
            {doc.number && <span>{t("admin.documents.labels.number")} {doc.number}</span>}
            {doc.issue_date && (
              <span>
                {t("admin.documents.labels.issue_date")} {formatDate(doc.issue_date)}
              </span>
            )}
            {doc.expire_date && (
              <span>
                {t("admin.documents.labels.expire_date")} {formatDate(doc.expire_date)}
              </span>
            )}
            {doc.created_at && (
              <span>
                {t("admin.documents.labels.created_at")} {formatDate(doc.created_at)}
              </span>
            )}
            <div className="flex gap-2 pt-1">
              <button type="button" className="btn-secondary btn-xs" onClick={toggleExpanded}>
                {expanded ? t("admin.documents.actions.collapse") : t("admin.documents.actions.expand")}
              </button>
              <button
                type="button"
                className="btn-primary btn-xs"
                onClick={() => openDoc(doc)}
                disabled={synthetic}
              >
                {t("admin.documents.actions.open")}
              </button>
            </div>
          </div>
        </div>

        {expanded && (
          <div className="mt-3 space-y-3 border-t border-gray-100 pt-3 text-xs text-gray-600">
            {synthetic ? (
              <div className="rounded border border-dashed border-amber-200 bg-amber-50 px-3 py-2 text-amber-700">
                {t("admin.documents.messages.checklist_placeholder")}
                {requirementSources.length > 0 && (
                  <span className="ml-1 text-amber-600">
                    {t("admin.documents.labels.required_sources", {
                      values: { sources: requirementSources.join(", ") },
                    })}
                  </span>
                )}
              </div>
            ) : (
              requirementSources.length > 0 && (
                <div className="rounded border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] text-slate-600">
                  {t("admin.documents.labels.required_sources", {
                    values: { sources: requirementSources.join(", ") },
                  })}
                </div>
              )
            )}

            <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2">
              <span>{t("admin.documents.table.status")}</span>
              <select
                className="input input-sm"
                value={selectStatus}
                onChange={(e) => updateStatus(doc, e.target.value as DocumentStatus)}
                disabled={!canManageDocuments || statusUpdating[doc.id] || synthetic}
              >
                {Object.keys(DOCUMENT_STATUS_META).map((status) => (
                  <option key={status} value={status}>
                    {translateStatus(status)}
                  </option>
                ))}
              </select>
            </label>
              <button
                className="btn-primary btn-xs"
                onClick={() => approveDocument(doc)}
                disabled={!canManageDocuments || statusUpdating[doc.id] || selectStatus === "approved" || synthetic}
              >
                {t("admin.documents.actions.approve")}
              </button>
              <button
                className="btn-ghost btn-xs border border-rose-200 text-rose-600 hover:bg-rose-50"
                onClick={() => rejectDocument(doc)}
                disabled={!canManageDocuments || statusUpdating[doc.id] || synthetic}
              >
                {t("admin.documents.actions.reject")}
              </button>
              {canManageDocuments && !synthetic && (
                <button
                  className="btn-danger btn-xs"
                  onClick={() => doDelete(doc.id)}
                  disabled={statusUpdating[doc.id]}
                >
                  {t("common.actions.delete")}
                </button>
              )}
              {statusUpdating[doc.id] && (
                <span className="text-[11px] text-gray-500">{t("admin.documents.status.saving")}</span>
              )}
            </div>

            {!synthetic ? (
              <div className="rounded border border-dashed border-gray-300 bg-gray-50 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <label className="input flex cursor-pointer items-center gap-3">
                    <span className="truncate text-xs">
                      {selectedReplaceFile
                        ? selectedReplaceFile.name
                        : t("admin.documents.forms.replace_file_placeholder")}
                    </span>
                    <span className="btn-secondary btn-xs">{t("admin.documents.actions.choose_file")}</span>
                    <input
                      type="file"
                      className="hidden"
                      onChange={(e) => {
                        const next = e.currentTarget.files?.[0] ?? null;
                        e.currentTarget.value = "";
                        if (next && isTooLarge(next)) {
                          setError(t("admin.documents.errors.file_too_large", { values: { limit: MAX_FILE_MB } }));
                          return;
                        }
                        setError(null);
                        setReplaceFile((prev) => ({ ...prev, [doc.id]: next }));
                      }}
                    />
                  </label>
                  <button
                    className="btn-primary btn-xs"
                    onClick={handleReplaceUpload}
                    disabled={!selectedReplaceFile || isReplacing}
                  >
                    {isReplacing
                      ? t("admin.documents.status.uploading_with_progress", { values: { percent: uploadProgress } })
                      : t("admin.documents.actions.upload_file")}
                  </button>
                  <button
                    className="btn-ghost btn-xs"
                    onClick={() => setReplaceFile((prev) => ({ ...prev, [doc.id]: null }))}
                    disabled={!selectedReplaceFile || isReplacing}
                  >
                    {t("common.actions.clear")}
                  </button>
                </div>
                {isReplacing && (
                  <div className="mt-2 h-1.5 rounded bg-gray-200">
                    <div
                      className="h-full rounded bg-blue-500 transition-all"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                )}
              </div>
            ) : (
              canManageDocuments && (
                <button
                  className="btn-primary btn-xs"
                  onClick={() => createDocumentFromChecklist(doc)}
                  disabled={statusUpdating[doc.id]}
                >
                  {t("admin.documents.actions.create_document")}
                </button>
              )
            )}

            <div className="space-y-2 rounded border border-gray-100 bg-gray-50 p-3">
              <div className="text-[11px] font-semibold uppercase text-gray-500">
                {t("admin.documents.forms.core.title")}
              </div>
              <div className="grid gap-2 md:grid-cols-3">
                <label className="block">
                  <div className="text-[11px] text-gray-500">{t("admin.documents.forms.core.number")}</div>
                  <input
                    className="input input-sm mt-1"
                    type="text"
                    value={core.number ?? ""}
                    onChange={(e) => updateCoreField("number", e.target.value)}
                    disabled={!canManageDocuments || synthetic}
                  />
                </label>
                <label className="block">
                  <div className="text-[11px] text-gray-500">{t("admin.documents.forms.core.requested_from")}</div>
                  <select
                    className="input input-sm mt-1"
                    value={core.requested_from ?? doc.requested_from}
                    onChange={(e) => updateCoreField("requested_from", e.target.value as DocumentRequestedFrom)}
                    disabled={!canManageDocuments || synthetic}
                  >
                    {Object.entries(REQUESTED_FROM_LABEL_KEYS).map(([value, key]) => (
                      <option key={value} value={value}>
                        {t(key, { defaultValue: value })}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <div className="text-[11px] text-gray-500">{t("admin.documents.forms.core.owner")}</div>
                  <input
                    className="input input-sm mt-1"
                    type="text"
                    value={core.owner_id ?? ""}
                    onChange={(e) => updateCoreField("owner_id", e.target.value)}
                    disabled={!canManageDocuments || synthetic}
                  />
                </label>
                {isOrderableDoc && (
                  <>
                    <label className="block">
                      <div className="text-[11px] text-gray-500">{t("admin.documents.forms.ordered_at")}</div>
                      <input
                        className="input input-sm mt-1"
                        type="date"
                        value={core.ordered_at ? String(core.ordered_at).slice(0, 10) : ""}
                        onChange={(e) => updateCoreField("ordered_at", e.target.value)}
                        disabled={!canManageDocuments || synthetic}
                      />
                    </label>
                    <label className="block">
                      <div className="text-[11px] text-gray-500">{t("admin.documents.forms.valid_from")}</div>
                      <input
                        className="input input-sm mt-1"
                        type="date"
                        value={core.valid_from ? String(core.valid_from).slice(0, 10) : ""}
                        onChange={(e) => updateCoreField("valid_from", e.target.value)}
                        disabled={!canManageDocuments || synthetic}
                      />
                    </label>
                    <label className="block">
                      <div className="text-[11px] text-gray-500">{t("admin.documents.forms.remind_in_days")}</div>
                      <input
                        className="input input-sm mt-1"
                        type="number"
                        min={0}
                        value={
                          core.reminder_days_before === null || core.reminder_days_before === undefined
                            ? ""
                            : core.reminder_days_before
                        }
                        onChange={(e) =>
                          updateCoreField(
                            "reminder_days_before",
                            e.target.value === "" ? null : Number(e.target.value)
                          )
                        }
                        disabled={!canManageDocuments || synthetic}
                      />
                    </label>
                  </>
                )}
                <label className="block">
                  <div className="text-[11px] text-gray-500">{t("admin.documents.forms.issue_date")}</div>
                  <input
                    className="input input-sm mt-1"
                    type="date"
                    value={core.issue_date ? String(core.issue_date).slice(0, 10) : ""}
                    onChange={(e) => updateCoreField("issue_date", e.target.value)}
                    disabled={!canManageDocuments || synthetic}
                  />
                </label>
                <label className="block">
                  <div className="text-[11px] text-gray-500">{t("admin.documents.forms.expire_date")}</div>
                  <input
                    className="input input-sm mt-1"
                    type="date"
                    value={core.expire_date ? String(core.expire_date).slice(0, 10) : ""}
                    onChange={(e) => updateCoreField("expire_date", e.target.value)}
                    disabled={!canManageDocuments || synthetic}
                  />
                </label>
                <label className="md:col-span-3 block">
                  <div className="text-[11px] text-gray-500">{t("admin.documents.forms.comment_field")}</div>
                  <textarea
                    className="input mt-1 h-20"
                    value={core.comment ?? ""}
                    onChange={(e) => updateCoreField("comment", e.target.value)}
                    disabled={!canManageDocuments || synthetic}
                  />
                </label>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                className="btn-primary btn-xs"
                onClick={() => saveCoreFields(doc)}
                disabled={!canManageDocuments || synthetic || coreSaving[doc.id]}
              >
                {coreSaving[doc.id] ? t("admin.documents.status.saving") : t("common.actions.save")}
              </button>
              <button
                className="btn-ghost btn-xs"
                onClick={() => resetCoreFields(doc)}
                disabled={coreSaving[doc.id]}
              >
                {t("common.actions.reset")}
              </button>
            </div>
          </div>
          {metadataFields.length > 0 && (
            <div className="space-y-2 rounded border border-gray-100 bg-white p-3">
              <div className="text-[11px] font-semibold uppercase text-gray-500">
                {t("admin.documents.forms.metadata_section")}
              </div>
              <div className="grid gap-2 md:grid-cols-3">
                {metadataFields.map((field) => (
                  <div key={field.name}>
                    {renderMetadataFieldInput(
                      field,
                      metadataValues[field.name],
                      (next) =>
                        setMetadataEdits((prev) => ({
                          ...prev,
                          [doc.id]: { ...(prev[doc.id] ?? {}), [field.name]: next },
                        })),
                      !canManageDocuments || synthetic
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {renderWorkflow(doc)}
          {renderReminders(doc)}
          {renderLastCheck(doc)}
          </div>
        )}
      </div>
    );
  };

  const totalDocs = docs.length;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="text-lg font-semibold">{t("admin.documents.table.title")}</div>
          <div className="text-xs text-gray-500">
            {loading
              ? t("admin.documents.status.refreshing")
              : t("admin.documents.table.showing", { values: { filtered: filteredCount, total: totalDocs } })}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-secondary" onClick={loadAll} disabled={loading}>
            {loading ? t("admin.documents.status.refreshing") : t("admin.documents.actions.refresh")}
          </button>
        </div>
      </div>

      {error && <div className="rounded border border-rose-200 bg-rose-50 p-2 text-sm text-rose-700">{error}</div>}
      {info && <div className="rounded border border-green-200 bg-green-50 p-2 text-sm text-green-700">{info}</div>}

      {summary && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="space-y-1 rounded border border-gray-200 bg-white p-3 shadow-sm">
            <div className="text-xs uppercase text-gray-500">{t("admin.documents.table.status")}</div>
            <div className="text-2xl font-semibold text-gray-800">
              {summary.status === "no_required"
                ? t("admin.documents.summary.required_none")
                : `${summary.percent_ready}%`}
            </div>
            <div className="text-xs text-gray-500">
              {summary.status === "no_required"
                ? t("admin.documents.summary.required_empty")
                : t("admin.documents.summary.required_ready", {
                    values: {
                      ready: summary.required.ready,
                      total: summary.required.total,
                    },
                  })}
            </div>
            {summary.expiring_soon?.length > 0 && (
              <div className="text-xs text-amber-700">
                {t("admin.documents.summary.expiring", {
                  values: {
                    list: summary.expiring_soon
                      .slice(0, 2)
                      .map((entry) => entry.type)
                      .join(", "),
                  },
                })}
                {summary.expiring_soon.length > 2 ? "…" : ""}
              </div>
            )}
          </div>
          {KIND_ORDER.map((kind) => {
            const stats = statsByKind[kind];
            const progress = stats.total ? Math.round((stats.ready / stats.total) * 100) : 0;
            return (
              <div key={kind} className="space-y-1 rounded border border-gray-200 bg-white p-3 shadow-sm">
                <div className="text-sm font-semibold text-gray-700">{translateKind(kind)}</div>
                <div className="h-1.5 rounded bg-gray-200">
                  <div className="h-full rounded bg-blue-500" style={{ width: `${progress}%` }} />
                </div>
                <div className="text-xs text-gray-500">
                  {t("admin.documents.summary.stats", {
                    values: {
                      ready: stats.ready,
                      total: stats.total,
                      attention: stats.attention,
                      negative: stats.negative,
                    },
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {requiredEntries.length > 0 && (
        <div className="space-y-3 rounded border border-blue-100 bg-blue-50 p-3 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm font-semibold text-blue-900">{t('admin.documents.summary.required_for_vacancy')}</div>
            <div className="text-xs text-blue-700">
              {t('admin.documents.summary.required_counts', {
                values: {
                  total: summary?.required?.total ?? 0,
                  ready: summary?.required?.ready ?? 0,
                  in_progress: summary?.required?.in_progress ?? 0,
                  problems: summary?.required?.problems ?? (Array.isArray(summary?.required?.problematic) ? summary?.required?.problematic?.length : 0),
                  missing: summary?.required?.missing_count ?? (Array.isArray(summary?.required?.missing) ? summary?.required?.missing?.length : 0),
                },
              })}
            </div>
          </div>
          <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
            {requiredEntries.map((entry) => {
              const badge = REQUIRED_STATUS_META[entry.status];
              const typeInfo = typeByCode.get(entry.type);
              const orderDraft = orderDraftForType(entry.type);
              const isOrdering = Boolean(orderingTypes[entry.type]);
              const canOrderType =
                canManageDocuments && Boolean(typeInfo?.orderable) && entry.documents.length === 0;
              return (
                <div key={entry.type} className="rounded border border-white/60 bg-white/90 p-3 text-xs text-gray-700 shadow-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-gray-800">{entry.label}</span>
                    <span className={clsx("inline-flex items-center rounded-full px-2 py-0.5", badge.className)}>
                      {t(badge.labelKey, { defaultValue: entry.status })}
                    </span>
                  </div>
                  <div className="mt-2 space-y-1 text-[11px] text-gray-600">
                    {entry.documents.length > 0 ? (
                      entry.documents.map((item) => (
                        <div key={item.id} className="flex items-center gap-2">
                          <span>
                            {t(
                              DOCUMENT_STATUS_META[item.status as DocumentStatus]?.labelKey ?? item.status,
                              { defaultValue: item.status },
                            )}
                          </span>
                          {((item.meta_json as any)?.synthetic || (item.meta as any)?.synthetic) && (
                            <span className="text-amber-600">{t("admin.documents.badges.draft")}</span>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="text-gray-500">{t("admin.documents.labels.entry_missing")}</div>
                    )}
                  </div>
                  {canOrderType && (
                    <div className="mt-3 space-y-2 rounded border border-dashed border-indigo-200 bg-indigo-50/60 p-2 text-[11px] text-indigo-900">
                      <div className="text-xs font-semibold text-indigo-800">
                        {t("admin.documents.order_panel.no_data")}
                      </div>
                      <div className="grid gap-2 sm:grid-cols-2">
                        <label className="block">
                          <span className="text-[11px] uppercase tracking-wide text-indigo-700">
                            {t("admin.documents.forms.ordered_at")}
                          </span>
                          <input
                            type="date"
                            className="input input-sm mt-0.5"
                            value={orderDraft.ordered_at}
                            onChange={(e) => updateOrderDraftField(entry.type, "ordered_at", e.target.value)}
                          />
                        </label>
                        {entry.type === "work_permit" && (
                          <label className="block">
                            <span className="text-[11px] uppercase tracking-wide text-indigo-700">
                              {t("admin.documents.forms.requested_from_label")}
                            </span>
                            <input
                              type="date"
                              className="input input-sm mt-0.5"
                              value={orderDraft.requested_from ?? ""}
                              onChange={(e) => updateOrderDraftField(entry.type, "requested_from", e.target.value)}
                            />
                          </label>
                        )}
                      </div>
                      <button
                        type="button"
                        className="btn-primary btn-xs"
                        onClick={() => handleOrderType(entry.type)}
                        disabled={isOrdering}
                      >
                        {isOrdering
                          ? t("admin.documents.actions.ordering")
                          : t("admin.documents.actions.order")}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-5">
        <label className="block">
          <div className="label">{t("admin.documents.filters.group")}</div>
          <select
            className="input"
            value={kindFilter}
            onChange={(e) => setKindFilter(e.target.value === "all" ? "all" : (e.target.value as DocumentKind))}
          >
            <option value="all">{t("admin.documents.filters.all_groups", { defaultValue: "All" })}</option>
            {KIND_ORDER.map((kind) => (
              <option key={kind} value={kind}>
                {translateKind(kind)}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <div className="label">{t("admin.documents.filters.status")}</div>
          <select
            className="input"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value === "all" ? "all" : (e.target.value as DocumentStatus))}
          >
            <option value="all">{t("admin.documents.filters.any", { defaultValue: "Any" })}</option>
            {Object.keys(DOCUMENT_STATUS_META).map((value) => (
              <option key={value} value={value}>
                {translateStatus(value)}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <div className="label">{t("admin.documents.filters.ordered")}</div>
          <select
            className="input"
            value={orderedFilter}
            onChange={(e) => setOrderedFilter(e.target.value as "all" | "ordered" | "not_ordered")}
          >
            <option value="all">{t("admin.documents.filters.all", { defaultValue: "All" })}</option>
            <option value="ordered">{t("admin.documents.filters.ordered_only", { defaultValue: "Ordered only" })}</option>
            <option value="not_ordered">{t("admin.documents.filters.not_ordered", { defaultValue: "Not ordered" })}</option>
          </select>
        </label>
        <label className="block lg:col-span-2">
          <div className="label">{t("admin.documents.filters.search")}</div>
          <input
            className="input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t("admin.documents.filters.search_placeholder")}
          />
        </label>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={clsx("btn-xs", expiringSoonOnly ? "btn-primary" : "btn-secondary")}
          onClick={() => setExpiringSoonOnly((prev) => !prev)}
        >
          {t("admin.documents.badges.expiring", { values: { days: EXPIRING_SOON_THRESHOLD_DAYS } })}
        </button>
        <button
          type="button"
          className={clsx("btn-xs", passportIncompleteOnly ? "btn-primary" : "btn-secondary")}
          onClick={() => setPassportIncompleteOnly((prev) => !prev)}
        >
          {t("admin.documents.badges.passport_incomplete")}
        </button>
      </div>

      {canManageDocuments && (
        <div className="space-y-3 rounded border border-gray-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold text-gray-700">{t("admin.documents.actions.add_document")}</div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            <label className="block">
              <div className="label">{t("admin.documents.forms.type")}</div>
              <select
                className="input"
                value={selectedType}
                onChange={(e) => {
                  const value = e.target.value;
                  setSelectedType(value);
                  if (value !== "other") {
                    setCustomName("");
                    setCustomKind("driver");
                    setCustomRequester("driver");
                    setCustomProcessType("other");
                  }
                }}
              >
                {docTypes.map((type) => (
                  <option key={type.code} value={type.code}>
                    {type.name || type.code}
                    {type.required ? " *" : ""}
                  </option>
                ))}
              </select>
            </label>
            {selectedType === "other" ? (
              <>
                <label className="block">
                  <div className="label">{t("admin.documents.forms.custom_title")}</div>
                  <input
                    className="input"
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    placeholder={t("admin.documents.forms.custom_title_placeholder")}
                  />
                </label>
                <label className="block">
                  <div className="label">{t("admin.documents.forms.category")}</div>
                  <select
                    className="input"
                    value={customKind}
                    onChange={(e) => {
                      const value = e.target.value as DocumentKind;
                      setCustomKind(value);
                      if (value !== "process") setCustomProcessType("other");
                    }}
                  >
                    {KIND_ORDER.map((kind) => (
                      <option key={kind} value={kind}>
                        {t(KIND_LABEL_KEYS[kind], { defaultValue: kind })}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <div className="label">{t("admin.documents.forms.requested_from")}</div>
                  <select
                    className="input"
                    value={customRequester}
                    onChange={(e) => setCustomRequester(e.target.value as DocumentRequestedFrom)}
                  >
                    {Object.entries(REQUESTED_FROM_LABEL_KEYS).map(([value, labelKey]) => (
                      <option key={value} value={value}>
                        {t(labelKey, { defaultValue: value })}
                      </option>
                    ))}
                  </select>
                </label>
                {customKind === "process" && (
                  <label className="block">
                    <div className="label">{t("admin.documents.forms.process_type")}</div>
                    <select
                      className="input"
                      value={customProcessType}
                      onChange={(e) => setCustomProcessType(e.target.value as DocumentProcessType)}
                    >
                      {Object.entries(PROCESS_LABEL_KEYS).map(([value, labelKey]) => (
                        <option key={value} value={value}>
                          {t(labelKey, { defaultValue: value })}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </>
            ) : (
              <label className="block">
                <div className="label">
                  {titleIsRequired
                    ? t("admin.documents.forms.custom_title")
                    : t("admin.documents.forms.custom_optional", {
                        values: { flag: t("admin.documents.forms.optional_hint") },
                      })}
                </div>
                <input
                  className="input"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder={t("admin.documents.forms.title_placeholder")}
                />
              </label>
            )}
          </div>
          {selectedType === "additional_document" && (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <label className="block">
                <div className="label">{t("admin.documents.forms.description")}</div>
                <textarea
                  className="input min-h-[96px]"
                  value={additionalDescription}
                  onChange={(e) => setAdditionalDescription(e.target.value)}
                  placeholder={t("admin.documents.forms.description_placeholder")}
                />
              </label>
              <label className="block">
                <div className="label">{t("admin.documents.forms.comment")}</div>
                <textarea
                  className="input min-h-[96px]"
                  value={additionalComment}
                  onChange={(e) => setAdditionalComment(e.target.value)}
                  placeholder={t("admin.documents.forms.comment_placeholder")}
                />
              </label>
            </div>
          )}
          {scannerRequirements && (
            <div className="rounded border border-dashed border-blue-200 bg-blue-50/70 p-3 text-xs text-blue-900">
              <div className="text-[11px] font-semibold uppercase text-blue-700">
                {t("admin.documents.scanner.section_title")}
              </div>
              <div className="text-sm font-medium">
                {scannerRequirements.title}
              </div>
              {scannerRequirements.details.length > 0 && (
                <ul className="mt-1 list-disc pl-4">
                  {scannerRequirements.details.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {creationMetadataFields.length > 0 && (
            <div className="rounded border border-gray-100 bg-white p-3">
              <div className="text-[11px] font-semibold uppercase text-gray-500">
                {t("admin.documents.forms.metadata_section")}
              </div>
              <div className="mt-2 grid gap-3 md:grid-cols-3">
                {creationMetadataFields.map((field) => (
                  <div key={field.name}>
                    {renderMetadataFieldInput(
                      field,
                      creationMetadata[field.name],
                      (next) =>
                        setCreationMetadata((prev) => ({
                          ...prev,
                          [field.name]: next,
                        })),
                      creatingDocument
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {selectedDocDefinition?.orderable && (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <label className="block">
                <div className="label">{t("admin.documents.forms.status")}</div>
                <select
                  className="input"
                  value={creationStatus}
                  onChange={(e) => setCreationStatus(e.target.value as DocumentStatus)}
                >
                  {CREATION_STATUS_OPTIONS.map((status) => (
                    <option key={status} value={status}>
                      {t(DOCUMENT_STATUS_META[status]?.labelKey ?? status, { defaultValue: status })}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <div className="label">{t("admin.documents.forms.ordered_at")}</div>
                <input
                  className="input"
                  type="date"
                  value={creationOrderedAt}
                  onChange={(e) => setCreationOrderedAt(e.target.value)}
                />
              </label>
              <label className="block">
                <div className="label">{t("admin.documents.forms.valid_from")}</div>
                <input
                  className="input"
                  type="date"
                  value={creationValidFrom}
                  onChange={(e) => setCreationValidFrom(e.target.value)}
                />
              </label>
              <label className="block">
                <div className="label">{t("admin.documents.forms.remind_in_days")}</div>
                <input
                  className="input"
                  type="number"
                  min="0"
                  max="365"
                  placeholder={t("admin.documents.forms.reminder_placeholder")}
                  value={creationReminderDays}
                  onChange={(e) => setCreationReminderDays(e.target.value)}
                />
              </label>
            </div>
          )}
        <div className="grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
          <label className="block" onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }} onDrop={(e) => { e.preventDefault(); e.stopPropagation(); const dropped = e.dataTransfer?.files?.[0]; if (dropped) { if (isTooLarge(dropped)) { setError(t("admin.documents.errors.file_too_large", { values: { limit: MAX_FILE_MB } })); return; } setError(null); setFile(dropped); } }}>
            <div className="label">{t("admin.documents.forms.file")}</div>
            <label className="input flex cursor-pointer items-center justify-between gap-3">
              <span className="truncate">
                {file ? file.name : t("admin.documents.forms.file_placeholder")}
              </span>
              <span className="btn-secondary btn-sm">{t("admin.documents.actions.choose_file")}</span>
              <input
                type="file"
                className="hidden"
                  onChange={(e) => {
                    const next = e.currentTarget.files?.[0] || null;
                    if (next && isTooLarge(next)) {
                      setError(t("admin.documents.errors.file_too_large", { values: { limit: MAX_FILE_MB } }));
                      return;
                    }
                    setError(null);
                    setFile(next);
                  }}
                />
              </label>
            </label>
            <div className="flex flex-col gap-2 md:items-end">
              {selectedDocDefinition?.orderable && (
                <button
                  className={clsx(
                    "btn-secondary",
                    (creatingDocument || uploading) && "opacity-60 pointer-events-none"
                  )}
                  onClick={createDocumentWithoutFile}
                  disabled={
                    !selectedType ||
                    creatingDocument ||
                    uploading ||
                    (selectedType === "other" && !customName.trim())
                  }
                >
                  {creatingDocument ? t("admin.documents.status.saving") : t("admin.documents.forms.submit_without_file")}
                </button>
              )}
              <button
                className={clsx("btn-primary", uploading && "opacity-60 pointer-events-none")}
                onClick={doUpload}
                disabled={!file || !selectedType || uploading}
              >
                {uploading ? t("admin.documents.status.uploading") : t("admin.documents.forms.upload_file")}
              </button>
            </div>
          </div>
          {uploading && (
            <div>
              <div className="h-2 overflow-hidden rounded bg-gray-200">
                <div className="h-full bg-blue-500 transition-all" style={{ width: `${uploadPct}%` }} />
              </div>
              <div className="mt-1 text-xs text-gray-500">
                {t("admin.documents.status.uploading_with_progress", { values: { progress: uploadPct } })}
              </div>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-gray-500">{t("common.loading")}</div>
      ) : filteredCount === 0 ? (
        <div className="rounded border border-dashed border-gray-300 bg-gray-50 p-6 text-sm text-gray-500">
          {docs.length ? t("admin.documents.filters.no_results") : t("admin.documents.filters.empty")}
        </div>
      ) : (
        <div className="space-y-4">
          {KIND_ORDER.map((kind) => {
            const items = groupedDocs[kind] ?? [];
            if (!items.length) return null;
            return (
              <section key={kind} className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold uppercase text-gray-600">
                    {translateKind(kind)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {t("admin.documents.table.items_count", { values: { count: items.length } })}
                  </div>
                </div>
                <div className="space-y-3">
                  {items.map((doc) => renderDocumentCard(doc))}
                </div>
              </section>
            );
          })}
        </div>
      )}

      {previewOpen && previewUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => {
            if (previewRevoker) {
              previewRevoker();
              setPreviewRevoker(null);
            }
            setPreviewOpen(false);
            setPreviewUrl(null);
            setPreviewContentType(null);
          }}
        >
          <div
            className="relative h-[90vh] w-full max-w-5xl overflow-hidden rounded bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="absolute right-3 top-3 rounded bg-black/40 px-2 py-1 text-xs text-white hover:bg-black/60"
              onClick={() => {
                if (previewRevoker) {
                  previewRevoker();
                  setPreviewRevoker(null);
                }
                setPreviewOpen(false);
                setPreviewUrl(null);
                setPreviewContentType(null);
              }}
            >
              {t("common.actions.close")}
            </button>
            <div className="h-full w-full overflow-auto">
              {previewContentType?.includes("pdf") || previewUrl.toLowerCase().endsWith(".pdf") ? (
                <iframe src={previewUrl} className="h-full w-full" />
              ) : (
                <img src={previewUrl} alt="preview" className="mx-auto block max-h-[85vh] w-auto" />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
