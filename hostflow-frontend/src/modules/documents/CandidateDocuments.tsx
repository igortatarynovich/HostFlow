import { useCallback, useEffect, useMemo, useState, useRef } from "react";
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
  listCandidateDocuments,
  orderDocument,
  exportCandidateBundle,
  listDocumentTemplates,
  applyDocumentTemplate,
  type DocumentTemplate,
} from "../../api/documents";
import type {
  Document,
  DocumentKind,
  DocumentStatus,
  DocumentRequestedFrom,
  DocumentProcessType,
  CandidateDocumentsSummaryResponse,
} from "../../api/types";
import type { CreateCandidateDocumentPayload, DocumentPatchPayload, DocumentOrderInput } from "../../api/documents";
import { usePermissions } from "../../hooks/usePermissions";
import { docsApi } from "../../api/client";
import { notifyCandidate } from "../../api/candidates";
import { useI18n } from "../../i18n";
import { usePlanLimitModal } from "../../contexts/PlanLimitModalContext";
import { formatErrorForDisplay } from "../../utils/errorHandling";
import { getDocumentConfigs, getRequiredDocumentTypeIds, isDefaultProfileWithEmptyDocumentConfig } from "../../utils/profileUtils";
import { DocumentFieldInput } from "./components/DocumentFieldInput";
import { DocumentCard } from "./components/DocumentCard";
import { useDocumentActions } from "./hooks/useDocumentActions";
import { useDocumentUpload } from "./hooks/useDocumentUpload";
import { useDocumentPreview } from "./hooks/useDocumentPreview";
import {
  DOCUMENT_STATUS_META,
  READINESS_STATE_META,
  KIND_LABEL_KEYS,
  KIND_ORDER,
  REQUESTED_FROM_LABEL_KEYS,
  PROCESS_LABEL_KEYS,
  READY_STATUSES,
  NEGATIVE_STATUSES,
  EQUIVALENT_TYPE_GROUPS,
  EXPIRING_SOON_THRESHOLD_DAYS,
  REQUIRED_STATUS_META,
  STATUS_FROM_RANK,
  READINESS_TO_STATUS,
  CREATION_STATUS_OPTIONS,
  CORE_METADATA_FIELDS,
  METADATA_LABEL_NS,
  DRIVER_DEFAULT_ENRICHMENT_CODES,
  MAX_FILE_MB,
} from "./constants";
import { getDocumentFieldsConfig } from "./documentFieldsConfig";
import {
  toArray,
  isTooLarge,
  formatDate,
  formatDateTime,
  dateValue,
  daysUntil,
  resolveDocumentUrl,
  guessPreviewable,
  detectPreviewMime,
  filenameFromUrl,
  isProbablyHtmlBlob,
  computeTodayIso,
  normalizeDocTypeCode,
  resolveDocTypeLabel,
} from "./documentUtils";
import type { DocType, OrderDraft, MetadataFieldConfig, RequiredState, MetadataState, CoreFields } from "./types";

// Constants are now imported from ./constants

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

// STATUS_FROM_RANK and READINESS_TO_STATUS are now imported from ./constants

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



// Constants, types, and utilities are now imported from separate modules

// extractErrorMessages is now imported from utils/errorHandling

type Props = {
  candidateId: string;
  ownerContext?: Record<string, any>;
  onFieldsApplied?: (doc: Document, fields: Record<string, any>) => void;
  hideHeader?: boolean;
  candidateProfile?: import('../../api/candidate_profiles').CandidateProfile | null;
  initialType?: string;
  compactType?: boolean;
};

export default function CandidateDocuments({
  candidateId,
  ownerContext,
  onFieldsApplied,
  hideHeader,
  candidateProfile,
  initialType,
  compactType = false,
}: Props) {
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
  // Backend allows document mutations for anyone with candidate access in DOCUMENT_MUTATE_ROLES
  // (recruiter, supervisor, …). UI used only documents.manage, which also requires the
  // "documents" module cell to be editable — misconfigured matrices blocked recruiters who
  // could still edit candidates. Allow uploads when the user can manage the candidate.
  const canManageDocuments = can("documents.manage") || can("candidates.manage");
  const planLimitModal = usePlanLimitModal();

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

  // Preview state is now handled by useDocumentPreview hook

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
  const [missingOnly, setMissingOnly] = useState(false);
  const [passportIncompleteOnly, setPassportIncompleteOnly] = useState(false);
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [applyingTemplate, setApplyingTemplate] = useState(false);

  const typeByCode = useMemo(() => new Map(docTypes.map((t) => [t.code, t])), [docTypes]);
  const getDocTypeLabel = useCallback(
    (typeCode: string, dbName?: string | null) => resolveDocTypeLabel(t, typeCode, dbName),
    [t]
  );
  const selectedDocDefinition = useMemo(() => {
    if (!selectedType) return null;
    return typeByCode.get(normalizeDocTypeCode(selectedType)) ?? typeByCode.get(selectedType) ?? null;
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
      const [typesResp, summaryResp, docsResp] = await Promise.all([
        getDocumentTypes(),
        getSummary(candidateId, { context: ownerContext ?? undefined, fillMissing: true }),
        listCandidateDocuments(candidateId),
      ]);
      const allTypes = toArray<DocType>(typesResp);
      const localFieldMap = buildFieldMap(allTypes);
      
      // Фильтруем типы документов по профилю, если профиль задан
      // (кроме driver_ce_default с пустым document_configs = как без профиля).
      const profileFilterActive = Boolean(candidateProfile && !isDefaultProfileWithEmptyDocumentConfig(candidateProfile));
      const profileDocConfigs = profileFilterActive ? getDocumentConfigs(candidateProfile) : [];
      const profileConfigByTypeCode = new Map<string, (typeof profileDocConfigs)[number]>();
      let filteredTypes = allTypes;
      if (profileFilterActive) {
        const profileDocTypeIds = new Set(profileDocConfigs.map((c) => String(c.document_type_id)));
        const typeById = new Map(allTypes.map((type) => [String(type.id), type] as const));
        const typeByCodeLocal = new Map(allTypes.map((type) => [type.code, type] as const));

        // Resolve profile references robustly: profile may store type UUID or type code.
        profileDocConfigs.forEach((cfg) => {
          const ref = String(cfg.document_type_id);
          const normalizedRef = normalizeDocTypeCode(ref);
          const type =
            typeById.get(ref) ||
            typeByCodeLocal.get(normalizedRef) ||
            typeByCodeLocal.get(ref);
          if (type) {
            profileConfigByTypeCode.set(type.code, cfg);
          }
        });

        filteredTypes = allTypes.filter((type) => profileConfigByTypeCode.has(type.code));

        // Fallback for legacy mixed refs: direct match by either id or code.
        if (filteredTypes.length === 0 && profileDocTypeIds.size > 0) {
          filteredTypes = allTypes.filter((type) => {
            const normalizedCode = normalizeDocTypeCode(String(type.code));
            return (
              profileDocTypeIds.has(String(type.id)) ||
              profileDocTypeIds.has(String(type.code)) ||
              profileDocTypeIds.has(normalizedCode)
            );
          });
          filteredTypes.forEach((type) => {
            const cfg = profileDocConfigs.find(
              (c) =>
                String(c.document_type_id) === String(type.id) ||
                normalizeDocTypeCode(String(c.document_type_id)) === String(type.code) ||
                String(c.document_type_id) === String(type.code)
            );
            if (cfg) profileConfigByTypeCode.set(type.code, cfg);
          });
        }

        // Citronex broken default profile: enrich reduced legacy config to full driver set.
        if (candidateProfile?.code === "driver_ce_default" && filteredTypes.length > 0 && filteredTypes.length <= 6) {
          const merged = new Map(filteredTypes.map((type) => [type.code, type] as const));
          DRIVER_DEFAULT_ENRICHMENT_CODES.forEach((code) => {
            const normalizedCode = normalizeDocTypeCode(code);
            const type = typeByCodeLocal.get(normalizedCode) || typeByCodeLocal.get(code);
            if (type) merged.set(type.code, type);
          });
          filteredTypes = Array.from(merged.values());
        }

        // Safety net: never show an empty page due to broken profile references.
        if (filteredTypes.length === 0 && allTypes.length > 0) {
          console.warn("[CandidateDocuments] Profile document refs resolved to 0 types; falling back to all document types");
          filteredTypes = allTypes;
        }
      }
      
      setDocTypes(filteredTypes);
      setSummaryResponse(summaryResp);
      const summaryDocsRaw = Array.isArray(summaryResp?.documents)
        ? (summaryResp.documents as Document[])
        : [];
      const docsListRaw = Array.isArray(docsResp) ? docsResp : [];
      const allowedTypeCodes = new Set(filteredTypes.map((type) => normalizeDocTypeCode(type.code)));
      const summaryDocs = profileFilterActive
        ? summaryDocsRaw.filter((doc) => allowedTypeCodes.has(normalizeDocTypeCode(doc.type_code || doc.doc_type)))
        : summaryDocsRaw;
      const docsList = profileFilterActive
        ? docsListRaw.filter((doc) => allowedTypeCodes.has(normalizeDocTypeCode(doc.type_code || doc.doc_type)))
        : docsListRaw;
      
      // Объединяем реальные документы и синтетические из summary
      // summaryDocs содержит все документы включая синтетические (missing) с fillMissing: true
      // Важно: реальные документы ключуются по id (UUID), а синтетические из summary — по synthetic::<type>.
      // Без проверки типа получается дубль: один и тот же тип показывается и как реальный файл, и как synthetic.
      const allDocsMap = new Map<string, Document>();
      const existingTypeCodes = new Set<string>();
      
      // Сначала добавляем реальные документы
      docsList.forEach((doc) => {
        allDocsMap.set(doc.id, doc);
        if (doc.type_code || doc.doc_type) {
          existingTypeCodes.add(normalizeDocTypeCode(doc.type_code || doc.doc_type));
        }
      });
      
      // Затем добавляем записи из summary: синтетические — только если нет реального документа этого типа
      summaryDocs.forEach((doc) => {
        const typeNorm = normalizeDocTypeCode(doc.type_code || doc.doc_type);
        const isSynthetic = doc.id.startsWith("synthetic::");
        if (isSynthetic) {
          if (typeNorm && existingTypeCodes.has(typeNorm)) {
            return;
          }
          const key = typeNorm
            ? `synthetic::${typeNorm}`
            : `synthetic::${doc.type_code || doc.doc_type || "unknown"}`;
          if (!allDocsMap.has(key)) {
            allDocsMap.set(key, doc);
            if (typeNorm) existingTypeCodes.add(typeNorm);
          }
        } else if (!allDocsMap.has(doc.id)) {
          allDocsMap.set(doc.id, doc);
          if (typeNorm) existingTypeCodes.add(typeNorm);
        }
      });
      
      // Создаем синтетические документы для всех типов из docTypes, которых еще нет
      filteredTypes.forEach((type) => {
        const typeCode = type.code;
        const typeCodeNorm = normalizeDocTypeCode(typeCode);
        if (!existingTypeCodes.has(typeCodeNorm)) {
          const syntheticId = `synthetic::${typeCode}::${candidateId}`;
          const syntheticDoc: Document = {
            id: syntheticId,
            tenant_id: summaryResp?.candidate_id || "",
            candidate_id: candidateId,
            company_id: null,
            kind: (type.kind as DocumentKind) || "driver",
            doc_type: typeCode,
            type: typeCode,
            type_code: typeCode,
            custom_name: null,
            title: null,
            owner_type: "candidate",
            owner_id: candidateId,
            requested_from: (type.requested_from as DocumentRequestedFrom) || "candidate",
            process_type: (type.process_type as DocumentProcessType) || "manual",
            number: null,
            status: "missing" as DocumentStatus,
            reminder_days_before: (() => {
              // Используем alert_days_before_expiry из профиля, если есть
              if (profileFilterActive) {
                const docConfig = profileConfigByTypeCode.get(typeCode);
                if (docConfig?.alert_days_before_expiry) return docConfig.alert_days_before_expiry;
              }
              return type.default_expire_in_days || 30;
            })(),
            files: [],
            workflow: null,
            source: null,
            external_id: null,
            verified_at: null,
            issue_date: null,
            expire_date: null,
            issued_at: null,
            expires_at: null,
            meta: { synthetic: true, doc_type: typeCode },
            extra: { synthetic: true, doc_type: typeCode },
            meta_json: { synthetic: true, doc_type: typeCode },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            reminders: [],
            version: null,
            last_check: null,
            has_files: false,
            status_rank: 0,
            readiness_state: null,
            ordered_at: null,
            valid_from: null,
            comment: null,
            user_comment: null,
            note: null,
          };
          allDocsMap.set(syntheticId, syntheticDoc);
          existingTypeCodes.add(typeCodeNorm);
        }
      });
      
      const allDocs = Array.from(allDocsMap.values());
      setDocs(allDocs);

      const coreInitial: Record<string, CoreFields> = {};
      const metadataInitial: Record<string, MetadataState> = {};
      allDocs.forEach((doc) => {
        coreInitial[doc.id] = coreFromDocument(doc);
        metadataInitial[doc.id] = buildMetadataStateFromDoc(
          doc,
          localFieldMap.get(normalizeDocTypeCode(doc.doc_type || doc.type_code || "")) ?? []
        );
      });
      setCoreEdits(coreInitial);
      setMetadataEdits(metadataInitial);

      const defaultType = (() => {
        if (!filteredTypes.length) return "";
        const readyCodes = new Set(
          summaryDocs
            .filter((doc) => READY_STATUSES.has(doc.status))
            .map((doc) => normalizeDocTypeCode(doc.type_code || doc.doc_type || ""))
        );
        // Проверяем required из профиля или из типа документа
        const firstRequired = filteredTypes.find((t) => {
          if (profileFilterActive) {
            const docConfig = profileConfigByTypeCode.get(t.code);
            const isRequired = docConfig?.required || t.required;
            return Boolean(isRequired) && !readyCodes.has(t.code);
          }
          return t.required && !readyCodes.has(t.code);
        });
        return firstRequired?.code || filteredTypes[0].code;
      })();
      setSelectedType((prev) => {
        if (prev) return prev;
        if (initialType) {
          const normalized = normalizeDocTypeCode(initialType);
          const exists = filteredTypes.some((t) => t.code === initialType || normalizeDocTypeCode(t.code) === normalized);
          if (exists) return initialType;
        }
        return defaultType;
      });
    } catch (e: any) {
      const fallback = t("admin.documents.errors.load_failed");
      if (planLimitModal?.showPlanLimitIfNeeded(e, fallback)) {
        return;
      }
      const message = e?.response?.data?.detail || e?.message || fallback;
      setError(String(message));
    } finally {
      setLoading(false);
    }
  }, [candidateId, ownerContext, coreFromDocument, candidateProfile, planLimitModal, t]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const templatesList = await listDocumentTemplates(false);
        setTemplates(templatesList);
      } catch (e: any) {
        console.error("[CandidateDocuments] Failed to load templates:", e);
      }
    };
    if (canManageDocuments) {
      loadTemplates();
    }
  }, [canManageDocuments]);

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
    (doc: Document) => normalizeDocTypeCode(doc.doc_type || doc.type_code || "") === "passport" && !READY_STATUSES.has(primaryStatus(doc)),
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

  const UPCOMING_DAYS = 60;
  const upcomingDeadlines = useMemo(() => {
    const items: { dateIso: string; label: string; docId: string; docTitle: string; kind: "expiry" | "workflow_step"; stepCode?: string }[] = [];
    const today = computeTodayIso();
    const cutoff = new Date(Date.now() + UPCOMING_DAYS * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    docs.forEach((doc) => {
      const typeCode = normalizeDocTypeCode(doc.type_code || doc.doc_type || "");
      const typeInfo = typeByCode.get(typeCode) ?? typeByCode.get(doc.doc_type) ?? typeByCode.get(doc.type_code);
      const title = doc.title || doc.custom_name || getDocTypeLabel(typeCode || doc.doc_type, typeInfo?.name);
      const expiry = doc.expire_date || doc.expires_at;
      if (expiry && expiry >= today) {
        if (expiry <= cutoff) {
          items.push({ dateIso: expiry, label: title, docId: doc.id, docTitle: title, kind: "expiry" });
        }
      }
      const steps = doc.workflow?.steps ?? [];
      steps.forEach((step) => {
        if (step.due_at && !step.completed_at && step.status !== "completed") {
          const due = step.due_at.slice(0, 10);
          if (due >= today && due <= cutoff) {
            items.push({
              dateIso: due,
              label: step.title || step.code || "Step",
              docId: doc.id,
              docTitle: title,
              kind: "workflow_step",
              stepCode: step.code,
            });
          }
        }
      });
    });
    items.sort((a, b) => a.dateIso.localeCompare(b.dateIso));
    return items.slice(0, 15);
  }, [docs, typeByCode, getDocTypeLabel]);

  const upcomingDeadlinesByDate = useMemo(() => {
    const byDate = new Map<string, typeof upcomingDeadlines>();
    upcomingDeadlines.forEach((item) => {
      const key = item.dateIso.slice(0, 10);
      if (!byDate.has(key)) byDate.set(key, []);
      byDate.get(key)!.push(item);
    });
    return Array.from(byDate.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [upcomingDeadlines]);

  const groupedDocs = useMemo(() => {
    const search = searchQuery.trim().toLowerCase();
    const groups: Record<DocumentKind, Document[]> = { driver: [], employer: [], process: [] };

    docs.forEach((doc) => {
      if (kindFilter !== "all" && doc.kind !== kindFilter) return;
      const statusValue = primaryStatus(doc);
      if (statusFilter !== "all" && statusValue !== statusFilter) return;
      if (orderedFilter === "ordered" && !doc.ordered_at) return;
      if (orderedFilter === "not_ordered" && doc.ordered_at) return;
      if (search) {
        const typeCode = normalizeDocTypeCode(doc.type_code || doc.doc_type || "");
        const typeInfo = typeByCode.get(typeCode) ?? typeByCode.get(doc.doc_type) ?? typeByCode.get(doc.type_code);
        const typeName = getDocTypeLabel(typeCode || doc.doc_type, typeInfo?.name).toLowerCase();
        const title = (doc.title || doc.custom_name || "").toLowerCase();
        const rawType = (doc.doc_type || "").toLowerCase();
        if (!typeName.includes(search) && !title.includes(search) && !rawType.includes(search)) {
          return;
        }
      }
      if (expiringSoonOnly && !expiringSoonSet.has(doc.id)) return;
      if (missingOnly && primaryStatus(doc) !== "missing") return;
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
    orderedFilter,
    searchQuery,
    typeByCode,
    getDocTypeLabel,
    expiringSoonOnly,
    missingOnly,
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

  const orderableTypes = useMemo(
    () => docTypes.filter((t) => t.orderable),
    [docTypes]
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
  
  const filteredDocs = useMemo(() => {
    const all: Document[] = [];
    KIND_ORDER.forEach((kind) => {
      all.push(...(groupedDocs[kind] ?? []));
    });
    return all;
  }, [groupedDocs]);

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
    const readySet = new Set((reqSummary?.ready_types ?? []).map((item) => normalizeDocTypeCode(String(item))));
    const inProgressSet = new Set((reqSummary?.in_progress_types ?? []).map((item) => normalizeDocTypeCode(String(item))));
    const problemSet = new Set((reqSummary?.problematic ?? []).map((item) => normalizeDocTypeCode(String(item))));
    const missingSet = new Set((reqSummary?.missing ?? []).map((item) => normalizeDocTypeCode(String(item))));

    return checklist.requiredTypes.map((rawType) => {
      const typeCode = normalizeDocTypeCode(String(rawType));
      let status: RequiredState = "missing";
      if (readySet.has(typeCode)) status = "ready";
      else if (problemSet.has(typeCode)) status = "problem";
      else if (inProgressSet.has(typeCode)) status = "in_progress";
      else if (missingSet.has(typeCode)) status = "missing";
      const typeInfo = typeByCode.get(typeCode);
      const label = getDocTypeLabel(typeCode, typeInfo?.name);
      const documentsForType = docs.filter((doc) => normalizeDocTypeCode(doc.type_code || doc.doc_type || "") === typeCode);
      return { type: typeCode, label, status, documents: documentsForType };
    });
  }, [checklist, summary, docs, typeByCode, getDocTypeLabel]);


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
            values: { name: getDocTypeLabel(typeCode, typeInfo?.name) },
          }),
        );
        await loadAll();
      } catch (e: any) {
        if (
          planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.order_failed"))
        ) {
          return;
        }
        const message = formatErrorForDisplay(e, {
          fallback: t("admin.documents.notifications.order_failed"),
        });
        setError(message);
      } finally {
        setOrderingTypes((prev) => ({ ...prev, [typeCode]: false }));
      }
    },
    [
      canManageDocuments,
      candidateId,
      ownerContext,
      orderDraftForType,
      planLimitModal,
      typeByCode,
      updateDocumentState,
      loadAll,
      flash,
      updateOrderDraftField,
      getDocTypeLabel,
      t,
    ]
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
      // Для additional_document custom_name обязателен - устанавливаем его ПЕРВЫМ
      base.custom_name = trimmedTitle;
      base.title = trimmedTitle;
      metaPayload.title = trimmedTitle;
      metaPayload.description = desc;
      metaPayload.comment = commentValue;
      console.log("[buildCreatePayload] additional_document - set custom_name:", trimmedTitle, "base:", base);
    } else if (trimmedTitle) {
      base.title = trimmedTitle;
    }

    // Убеждаемся, что custom_name не перезаписывается undefined/null из restOverrides
    const merged: CreateCandidateDocumentPayload = { ...base, ...restOverrides };
    // Если custom_name был установлен в base, но перезаписан undefined/null, восстанавливаем его
    if (selectedType === "additional_document") {
      if (base.custom_name && !merged.custom_name) {
        merged.custom_name = base.custom_name;
      }
      // Также убеждаемся, что title установлен, если custom_name есть
      if (merged.custom_name && !merged.title) {
        merged.title = merged.custom_name;
      }
      // Если custom_name все еще отсутствует, но есть title, используем его
      if (!merged.custom_name && merged.title) {
        merged.custom_name = merged.title;
      }
      console.log("[buildCreatePayload] additional_document merged:", {
        "base.custom_name": base.custom_name,
        "merged.custom_name": merged.custom_name,
        "merged.title": merged.title,
        "merged.meta_json": merged.meta_json
      });
    }
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
    
    // ФИНАЛЬНАЯ проверка для additional_document - custom_name должен быть установлен
    if (selectedType === "additional_document" && !merged.custom_name) {
      // Пробуем найти в meta_json.title
      if (merged.meta_json?.title) {
        merged.custom_name = String(merged.meta_json.title).trim();
        console.warn("[buildCreatePayload] Restored custom_name from meta_json.title:", merged.custom_name);
      } else {
        console.error("[buildCreatePayload] CRITICAL ERROR: additional_document has no custom_name in final merged!", {
          base,
          merged,
          combinedMeta
        });
        throw new Error("custom_name is required for additional_document but was not set");
      }
    }
    
    console.log("[buildCreatePayload] Final merged for", selectedType, ":", {
      custom_name: merged.custom_name,
      title: merged.title,
      "meta_json.title": merged.meta_json?.title
    });
    
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
      if (
        planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.upload_failed"))
      ) {
        return;
      }
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
      if (
        planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.create_failed"))
      ) {
        return;
      }
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
      if (
        planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.delete_failed"))
      ) {
        return;
      }
      const message =
        e?.response?.data?.detail || e?.message || t("admin.documents.notifications.delete_failed");
      setError(String(message));
    }
  };

  // Document preview is now handled by useDocumentPreview hook
  const { previewUrl, previewOpen, previewContentType, openDoc, closePreview } = useDocumentPreview({ setError });
  const initialTypeAutoOpenedRef = useRef<string | null>(null);

  useEffect(() => {
    initialTypeAutoOpenedRef.current = null;
  }, [candidateId, initialType]);

  useEffect(() => {
    if (!initialType) return;
    if (initialTypeAutoOpenedRef.current === initialType) return;

    const normalizedInitial = normalizeDocTypeCode(initialType);
    const candidates = docs.filter((doc) => {
      const docType = normalizeDocTypeCode(doc.type_code || doc.doc_type || "");
      if (docType !== normalizedInitial) return false;
      const hasFiles = doc.has_files ?? (Array.isArray(doc.files) && doc.files.length > 0);
      return Boolean(hasFiles);
    });
    if (!candidates.length) return;

    candidates.sort((a, b) => {
      const aReady = READY_STATUSES.has(primaryStatus(a));
      const bReady = READY_STATUSES.has(primaryStatus(b));
      if (aReady !== bReady) return aReady ? -1 : 1;
      return dateValue(b.updated_at ?? b.created_at ?? null) - dateValue(a.updated_at ?? a.created_at ?? null);
    });

    initialTypeAutoOpenedRef.current = initialType;
    void openDoc(candidates[0]);
  }, [candidateId, docs, initialType, openDoc]);

  // Функция для получения значения поля из документа
  const getFieldValue = useCallback((doc: Document, fieldKey: string, metadataValues: MetadataState): any => {
    // Сначала проверяем редактируемые значения
    const coreEdit = coreEdits[doc.id];
    const metaEdit = metadataValues[fieldKey];
    
    // Core поля
    if (fieldKey === "number") {
      return coreEdit?.number !== undefined ? coreEdit.number : (doc.number ?? "");
    }
    if (fieldKey === "issue_date") {
      return coreEdit?.issue_date !== undefined ? coreEdit.issue_date : (doc.issue_date ?? "");
    }
    if (fieldKey === "expire_date") {
      return coreEdit?.expire_date !== undefined ? coreEdit.expire_date : (doc.expire_date ?? "");
    }
    if (fieldKey === "valid_from") {
      return coreEdit?.valid_from !== undefined ? coreEdit.valid_from : (doc.valid_from ?? "");
    }
    if (fieldKey === "ordered_at") {
      return coreEdit?.ordered_at !== undefined ? coreEdit.ordered_at : (doc.ordered_at ?? "");
    }
    
    // Метаданные - сначала проверяем редактируемые значения, затем из документа
    if (metaEdit !== undefined) {
      return metaEdit;
    }
    const meta = doc.meta_json ?? doc.meta ?? {};
    return meta[fieldKey] ?? "";
  }, [coreEdits]);

  // Document actions are now handled by useDocumentActions hook
  const {
    updateStatus,
    approveDocument,
    rejectDocument,
    saveCoreFields,
    deleteDocumentFile,
    createDocumentFromChecklist,
  } = useDocumentActions({
    candidateId,
    canManageDocuments,
    updateDocumentState,
    loadAll,
    setError,
    setStatusUpdating,
    setCoreSaving,
    flash,
    coreEdits,
    metadataEdits,
    getFieldValue,
    coreFromDocument,
    onFieldsApplied,
  });

  // Document upload is now handled by useDocumentUpload hook
  const { handleReplaceUpload: handleReplaceUploadHook } = useDocumentUpload({
    canManageDocuments,
    createDocumentFromChecklist,
    loadAll,
    setError,
    setReplaceUploading,
    setReplacePct,
    setReplaceFile,
    flash,
  });

  // Функция для обновления значения поля
  const updateFieldValue = (doc: Document, fieldKey: string, value: any) => {
    // Core поля
    if (["number", "issue_date", "expire_date", "valid_from", "ordered_at"].includes(fieldKey)) {
      setCoreEdits((prev) => ({
        ...prev,
        [doc.id]: { ...(prev[doc.id] ?? coreFromDocument(doc)), [fieldKey]: value },
      }));
    } else {
      // Метаданные
      setMetadataEdits((prev) => ({
        ...prev,
        [doc.id]: { ...(prev[doc.id] ?? {}), [fieldKey]: value },
      }));
    }
  };

  // renderDocumentCard is now a component: DocumentCard

  const totalDocs = docs.length;

  const [downloadingProfile, setDownloadingProfile] = useState(false);
  const [notifyingCandidate, setNotifyingCandidate] = useState(false);
  const [orderModalOpen, setOrderModalOpen] = useState(false);
  const [orderModalType, setOrderModalType] = useState<string>("");
  const [orderModalOrderedAt, setOrderModalOrderedAt] = useState<string>(() => computeTodayIso());
  const [orderModalRequestedFrom, setOrderModalRequestedFrom] = useState<string>("driver");

  const handleNotifyCandidate = async () => {
    if (!candidateId || !canManageDocuments) return;
    setNotifyingCandidate(true);
    setError(null);
    try {
      const result = await notifyCandidate(candidateId);
      if (result.sent) {
        flash(t("admin.documents.notifications.notify_candidate_sent", { defaultValue: "Email sent to candidate" }));
      } else {
        const reason = result.reason === "no_email"
          ? t("admin.documents.notifications.notify_candidate_no_email", { defaultValue: "Candidate has no email" })
          : t("admin.documents.notifications.notify_candidate_failed", { defaultValue: "Failed to send email" });
        setError(reason);
      }
    } catch (e: any) {
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          e,
          t("admin.documents.errors.notify_failed", { defaultValue: "Failed to notify candidate" }),
        )
      ) {
        return;
      }
      const message = e?.response?.data?.detail || e?.message || t("admin.documents.errors.notify_failed", { defaultValue: "Failed to notify candidate" });
      setError(String(message));
    } finally {
      setNotifyingCandidate(false);
    }
  };

  const handleDownloadProfile = async () => {
    if (!candidateId) return;
    setDownloadingProfile(true);
    setError(null);
    try {
      const blob = await exportCandidateBundle(candidateId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `candidate_${candidateId}_profile.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      flash(t("admin.documents.notifications.profile_downloaded", { defaultValue: "Profile downloaded" }));
    } catch (e: any) {
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          e,
          t("admin.documents.errors.download_failed", { defaultValue: "Failed to download profile" }),
        )
      ) {
        return;
      }
      const message = e?.response?.data?.detail || e?.message || t("admin.documents.errors.download_failed", { defaultValue: "Failed to download profile" });
      setError(String(message));
    } finally {
      setDownloadingProfile(false);
    }
  };

  const openOrderModal = useCallback(() => {
    const first = orderableTypes[0];
    setOrderModalType(first?.code ?? "");
    setOrderModalOrderedAt(orderDraftForType(first?.code ?? "").ordered_at || computeTodayIso());
    setOrderModalRequestedFrom((orderDraftForType(first?.code ?? "").requested_from as string) || "driver");
    setOrderModalOpen(true);
  }, [orderableTypes, orderDraftForType]);

  const handleOrderModalSubmit = useCallback(async () => {
    if (!orderModalType || !candidateId || !canManageDocuments) return;
    setOrderingTypes((prev) => ({ ...prev, [orderModalType]: true }));
    setError(null);
    try {
      const payload: DocumentOrderInput = {
        candidate_id: candidateId,
        doc_type: orderModalType,
        ordered_at: orderModalOrderedAt || undefined,
      };
      if (orderModalType === "work_permit") {
        payload.requested_from = orderModalRequestedFrom || undefined;
      }
      if (ownerContext && Object.keys(ownerContext).length > 0) {
        payload.owner_context = ownerContext;
      }
      const orderedDoc = await orderDocument(payload);
      updateDocumentState(orderedDoc);
      const typeInfo = typeByCode.get(orderModalType);
      flash(
        t("admin.documents.notifications.order_success", {
          values: { name: getDocTypeLabel(orderModalType, typeInfo?.name) },
        }),
      );
      await loadAll();
      setOrderModalOpen(false);
    } catch (e: any) {
      if (
        planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.order_failed"))
      ) {
        return;
      }
      const message = formatErrorForDisplay(e, {
        fallback: t("admin.documents.notifications.order_failed"),
      });
      setError(message);
    } finally {
      setOrderingTypes((prev) => ({ ...prev, [orderModalType]: false }));
    }
  }, [orderModalType, orderModalOrderedAt, orderModalRequestedFrom, candidateId, canManageDocuments, ownerContext, planLimitModal, typeByCode, updateDocumentState, loadAll, flash, t, getDocTypeLabel]);

  const handleApplyTemplate = async () => {
    if (!candidateId || !selectedTemplateId || !canManageDocuments) return;
    setApplyingTemplate(true);
    setError(null);
    try {
      const template = templates.find((t) => t.id === selectedTemplateId);
      if (!template) {
        setError(t("admin.documents.errors.template_not_found", { defaultValue: "Template not found" }));
        return;
      }
      const result = await applyDocumentTemplate(candidateId, { template_id: selectedTemplateId });
      flash(
        t("admin.documents.notifications.template_applied", {
          values: { created: result.created, updated: result.updated },
          defaultValue: `Template applied: ${result.created} created, ${result.updated} updated`,
        })
      );
      setSelectedTemplateId("");
      await loadAll();
    } catch (e: any) {
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          e,
          t("admin.documents.errors.template_apply_failed", { defaultValue: "Failed to apply template" }),
        )
      ) {
        return;
      }
      const message = e?.response?.data?.detail || e?.message || t("admin.documents.errors.template_apply_failed", { defaultValue: "Failed to apply template" });
      setError(String(message));
    } finally {
      setApplyingTemplate(false);
    }
  };

  return (
    <div className="space-y-4">
      {!hideHeader && (
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0">
            <span className="text-lg font-semibold">{t("admin.documents.table.title")}</span>
            {!loading ? (
              <span className="text-xs tabular-nums text-slate-500">
                {filteredCount}/{totalDocs}
              </span>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {templates.length > 0 && canManageDocuments ? (
              <>
                <select
                  className="input max-w-[13rem] min-w-0 flex-1 text-sm sm:flex-none"
                  aria-label={t("admin.documents.template.select", { defaultValue: "Template" })}
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  disabled={applyingTemplate || loading}
                >
                  <option value="">
                    {t("admin.documents.template.select", { defaultValue: "Select template..." })}
                  </option>
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn-primary btn-sm shrink-0"
                  onClick={handleApplyTemplate}
                  disabled={!selectedTemplateId || applyingTemplate || loading}
                >
                  {applyingTemplate
                    ? t("admin.documents.status.applying", { defaultValue: "Applying..." })
                    : t("admin.documents.actions.apply_template", { defaultValue: "Apply template" })}
                </button>
              </>
            ) : null}
            {canManageDocuments && orderableTypes.length > 0 ? (
              <button type="button" className="btn-secondary btn-sm shrink-0" onClick={openOrderModal} disabled={loading}>
                {t("admin.documents.actions.order_document", { defaultValue: "Order document" })}
              </button>
            ) : null}
            {canManageDocuments ? (
              <button
                type="button"
                className="btn-primary btn-sm shrink-0"
                onClick={handleNotifyCandidate}
                disabled={notifyingCandidate || loading}
              >
                {notifyingCandidate
                  ? t("admin.documents.status.sending", { defaultValue: "Sending..." })
                  : t("admin.documents.actions.notify_candidate", { defaultValue: "Notify candidate" })}
              </button>
            ) : null}
            <button
              type="button"
              className="btn-secondary btn-sm shrink-0"
              onClick={handleDownloadProfile}
              disabled={downloadingProfile || loading}
            >
              {downloadingProfile
                ? t("admin.documents.status.downloading", { defaultValue: "Downloading..." })
                : t("admin.documents.actions.download_profile", { defaultValue: "Download profile" })}
            </button>
            <button type="button" className="btn-secondary btn-sm shrink-0" onClick={loadAll} disabled={loading}>
              {loading ? t("admin.documents.status.refreshing") : t("admin.documents.actions.refresh")}
            </button>
          </div>
        </div>
      )}

      {error ? (
        <div className="rounded border border-rose-200 bg-rose-50 px-2 py-1.5 text-sm text-rose-700">{error}</div>
      ) : null}
      {info ? (
        <div className="rounded border border-green-200 bg-green-50 px-2 py-1.5 text-sm text-green-700">{info}</div>
      ) : null}

      {!hideHeader && upcomingDeadlinesByDate.length > 0 && (
        <details className="rounded-lg border border-slate-200 bg-white">
          <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50">
            {t("admin.documents.upcoming_deadlines.title")} ({upcomingDeadlines.length})
          </summary>
          <div className="space-y-3 border-t border-slate-100 px-3 py-2">
            {upcomingDeadlinesByDate.map(([dateIso, dateItems]) => {
              const dateStr = formatDate(dateIso);
              return (
                <div key={dateIso}>
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    {dateStr}
                  </div>
                  <ul className="space-y-1 text-sm text-slate-600">
                    {dateItems.map((item, idx) => {
                      const days = daysUntil(item.dateIso);
                      const isExpired = days !== null && days < 0;
                      const subLabel =
                        item.kind === "workflow_step"
                          ? t("admin.documents.upcoming_deadlines.step_due", { values: { step: item.label } })
                          : isExpired
                            ? t("admin.documents.upcoming_deadlines.expired")
                            : days !== null
                              ? t("admin.documents.upcoming_deadlines.expires_in_days", { values: { days } })
                              : "";
                      return (
                        <li key={`${item.docId}-${item.kind}-${item.stepCode ?? ""}-${idx}`} className="flex flex-wrap items-baseline gap-x-2">
                          <span>{item.docTitle}</span>
                          {subLabel ? <span className="text-slate-500">{subLabel}</span> : null}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
          </div>
        </details>
      )}

      {!hideHeader && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
          <select
            className="input max-w-[130px] text-sm"
            aria-label={t("admin.documents.filters.kind")}
            value={kindFilter}
            onChange={(e) => setKindFilter(e.target.value === "all" ? "all" : (e.target.value as DocumentKind))}
          >
            <option value="all">{t("admin.documents.filters.all_kinds")}</option>
            {KIND_ORDER.map((kind) => (
              <option key={kind} value={kind}>
                {translateKind(kind)}
              </option>
            ))}
          </select>
          <select
            className="input max-w-[130px] text-sm"
            aria-label={t("admin.documents.filters.status")}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value === "all" ? "all" : (e.target.value as DocumentStatus))}
          >
            <option value="all">{t("admin.documents.filters.all_statuses")}</option>
            {Object.entries(DOCUMENT_STATUS_META).map(([value, meta]) => (
              <option key={value} value={value}>
                {t(meta.labelKey ?? value, { defaultValue: value })}
              </option>
            ))}
          </select>
          <select
            className="input max-w-[120px] text-sm"
            aria-label={t("admin.documents.filters.ordered")}
            value={orderedFilter}
            onChange={(e) => setOrderedFilter(e.target.value as "all" | "ordered" | "not_ordered")}
          >
            <option value="all">{t("admin.documents.filters.all")}</option>
            <option value="ordered">{t("admin.documents.filters.ordered_only")}</option>
            <option value="not_ordered">{t("admin.documents.filters.not_ordered")}</option>
          </select>
          <input
            type="search"
            className="input min-w-[8rem] flex-1 text-sm"
            aria-label={t("admin.documents.filters.search")}
            placeholder={t("admin.documents.filters.search_placeholder")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <label className="flex cursor-pointer items-center gap-1.5 whitespace-nowrap text-xs text-slate-600">
            <input
              type="checkbox"
              className="rounded border-slate-300"
              checked={expiringSoonOnly}
              onChange={(e) => setExpiringSoonOnly(e.target.checked)}
            />
            {t("admin.documents.filters.expiring_soon")}
          </label>
          <label className="flex cursor-pointer items-center gap-1.5 whitespace-nowrap text-xs text-slate-600">
            <input
              type="checkbox"
              className="rounded border-slate-300"
              checked={missingOnly}
              onChange={(e) => setMissingOnly(e.target.checked)}
            />
            {t("admin.documents.filters.missing_only")}
          </label>
          <label className="flex cursor-pointer items-center gap-1.5 whitespace-nowrap text-xs text-slate-600">
            <input
              type="checkbox"
              className="rounded border-slate-300"
              checked={passportIncompleteOnly}
              onChange={(e) => setPassportIncompleteOnly(e.target.checked)}
            />
            {t("admin.documents.filters.passport_incomplete")}
          </label>
        </div>
      )}

      {loading && docs.length === 0 ? (
        <div className="text-sm text-slate-500">{t("common.loading")}</div>
      ) : filteredCount === 0 ? (
        <div className="rounded border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
          {docs.length ? t("admin.documents.filters.no_results") : t("admin.documents.filters.empty")}
        </div>
      ) : compactType && selectedType ? (
        (() => {
          const normalizedSelected = normalizeDocTypeCode(selectedType);
          const typeDocs = docs
            .filter((doc) => {
              const docType = normalizeDocTypeCode(doc.type_code || doc.doc_type || "");
              return docType === normalizedSelected;
            })
            .filter((doc) => {
              const statusValue = primaryStatus(doc);
              if (statusFilter !== "all" && statusValue !== statusFilter) return false;
              if (orderedFilter === "ordered" && !doc.ordered_at) return false;
              if (orderedFilter === "not_ordered" && doc.ordered_at) return false;
              if (expiringSoonOnly && !expiringSoonSet.has(doc.id)) return false;
              if (missingOnly && primaryStatus(doc) !== "missing") return false;
              if (passportIncompleteOnly && !passportIncompleteSet.has(doc.id)) return false;
              if (searchQuery.trim()) {
                const search = searchQuery.trim().toLowerCase();
                const typeInfo = typeByCode.get(normalizeDocTypeCode(doc.type_code || doc.doc_type || "")) ?? typeByCode.get(doc.doc_type) ?? typeByCode.get(doc.type_code);
                const typeName = getDocTypeLabel(normalizeDocTypeCode(doc.type_code || doc.doc_type || ""), typeInfo?.name).toLowerCase();
                const title = (doc.title || doc.custom_name || "").toLowerCase();
                const rawType = (doc.doc_type || "").toLowerCase();
                if (!typeName.includes(search) && !title.includes(search) && !rawType.includes(search)) return false;
              }
              return true;
            })
            .sort((a, b) => {
              const statusA = primaryStatus(a);
              const statusB = primaryStatus(b);
              const rankA = DOCUMENT_STATUS_META[statusA]?.order ?? (typeof a.status_rank === "number" ? a.status_rank : 0);
              const rankB = DOCUMENT_STATUS_META[statusB]?.order ?? (typeof b.status_rank === "number" ? b.status_rank : 0);
              if (rankA !== rankB) return rankB - rankA;
              const orderedDiff = dateValue(b.ordered_at ?? null) - dateValue(a.ordered_at ?? null);
              if (orderedDiff !== 0) return orderedDiff;
              const expiresDiff = dateValue(a.expire_date ?? a.expires_at ?? null) - dateValue(b.expire_date ?? b.expires_at ?? null);
              if (expiresDiff !== 0) return expiresDiff;
              return (a.title || a.custom_name || a.doc_type).localeCompare(
                b.title || b.custom_name || b.doc_type,
                locale || undefined
              );
            });

          if (typeDocs.length === 0) {
            return <div className="text-sm text-slate-500">{t("admin.documents.filters.no_results", { defaultValue: "No results." })}</div>;
          }

          return (
            <div className="space-y-3">
              {typeDocs.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  doc={doc}
                  variant="compact"
                  typeByCode={typeByCode}
                  metadataFieldMap={metadataFieldMap}
                  coreEdits={coreEdits}
                  metadataEdits={metadataEdits}
                  statusUpdating={statusUpdating}
                  coreSaving={coreSaving}
                  replaceFile={replaceFile}
                  replacePct={replacePct}
                  replaceUploading={replaceUploading}
                  expandedDocs={expandedDocs}
                  canManageDocuments={canManageDocuments}
                  coreFromDocument={coreFromDocument}
                  translateStatus={translateStatus}
                  getFieldValue={getFieldValue}
                  updateFieldValue={updateFieldValue}
                  updateStatus={updateStatus}
                  approveDocument={approveDocument}
                  rejectDocument={rejectDocument}
                  saveCoreFields={saveCoreFields}
                  deleteDocumentFile={deleteDocumentFile}
                  deleteDocument={doDelete}
                  openDoc={openDoc}
                  handleReplaceUpload={handleReplaceUploadHook}
                  setReplaceFile={setReplaceFile}
                  setExpandedDocs={setExpandedDocs}
                  setError={setError}
                />
              ))}
            </div>
          );
        })()
      ) : (
        <div className="space-y-4">
          {KIND_ORDER.map((kind) => {
            const kindDocs = groupedDocs[kind] ?? [];
            if (kindDocs.length === 0) return null;

            const kindStats = statsByKind[kind];
            const kindLabel = translateKind(kind);

            return (
              <div key={kind} className="space-y-3">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 border-b border-slate-200 pb-2">
                  <h3 className="text-base font-semibold text-slate-900">
                    {kindLabel}
                    <span className="ml-2 text-sm font-normal text-slate-500">
                      ({kindStats.ready}/{kindStats.total} {t("admin.documents.counters.ready", { defaultValue: "ready" })})
                    </span>
                  </h3>
                  {kindStats.attention > 0 && (
                    <span className="text-xs text-amber-600">
                      {kindStats.attention} {t("admin.documents.counters.need_attention", { defaultValue: "need attention" })}
                    </span>
                  )}
                </div>
                <div className="space-y-3">
                  {kindDocs.map((doc) => (
                    <DocumentCard
                      key={doc.id}
                      doc={doc}
                      typeByCode={typeByCode}
                      metadataFieldMap={metadataFieldMap}
                      coreEdits={coreEdits}
                      metadataEdits={metadataEdits}
                      statusUpdating={statusUpdating}
                      coreSaving={coreSaving}
                      replaceFile={replaceFile}
                      replacePct={replacePct}
                      replaceUploading={replaceUploading}
                      expandedDocs={expandedDocs}
                      canManageDocuments={canManageDocuments}
                      coreFromDocument={coreFromDocument}
                      translateStatus={translateStatus}
                      getFieldValue={getFieldValue}
                      updateFieldValue={updateFieldValue}
                      updateStatus={updateStatus}
                      approveDocument={approveDocument}
                      rejectDocument={rejectDocument}
                      saveCoreFields={saveCoreFields}
                      deleteDocumentFile={deleteDocumentFile}
                      deleteDocument={doDelete}
                      openDoc={openDoc}
                      handleReplaceUpload={handleReplaceUploadHook}
                      setReplaceFile={setReplaceFile}
                      setExpandedDocs={setExpandedDocs}
                      setError={setError}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {orderModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setOrderModalOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 text-base font-semibold text-slate-900">
              {t("admin.documents.actions.order_document", { defaultValue: "Order document" })}
            </div>
            <div className="space-y-3">
              <select
                className="input w-full text-sm"
                aria-label={t("admin.documents.forms.type", { defaultValue: "Document type" })}
                value={orderModalType}
                onChange={(e) => {
                  const code = e.target.value;
                  setOrderModalType(code);
                  setOrderModalOrderedAt(orderDraftForType(code).ordered_at || computeTodayIso());
                  setOrderModalRequestedFrom((orderDraftForType(code).requested_from as string) || "driver");
                }}
              >
                <option value="">{t("admin.documents.template.select", { defaultValue: "Select..." })}</option>
                {orderableTypes.map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.name || t.code}
                  </option>
                ))}
              </select>
              <div
                className={clsx(
                  "grid gap-3",
                  orderModalType === "work_permit" ? "sm:grid-cols-2" : "grid-cols-1",
                )}
              >
                <input
                  type="date"
                  className="input w-full text-sm"
                  aria-label={t("admin.documents.forms.ordered_at", { defaultValue: "Ordered at" })}
                  value={orderModalOrderedAt.slice(0, 10)}
                  onChange={(e) => setOrderModalOrderedAt(e.target.value || computeTodayIso())}
                />
                {orderModalType === "work_permit" ? (
                  <select
                    className="input w-full text-sm"
                    aria-label={t("admin.documents.forms.requested_from", { defaultValue: "Requested from" })}
                    value={orderModalRequestedFrom}
                    onChange={(e) => setOrderModalRequestedFrom(e.target.value)}
                  >
                    {(["driver", "employer", "agency"] as const).map((val) => (
                      <option key={val} value={val}>
                        {translateRequestedFrom(val)}
                      </option>
                    ))}
                  </select>
                ) : null}
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setOrderModalOpen(false)}
              >
                {t("common.actions.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={!orderModalType || orderingTypes[orderModalType]}
                onClick={() => handleOrderModalSubmit()}
              >
                {orderingTypes[orderModalType]
                  ? t("admin.documents.status.ordering", { defaultValue: "Ordering..." })
                  : t("admin.documents.actions.order_document", { defaultValue: "Order document" })}
              </button>
            </div>
          </div>
        </div>
      )}

      {previewOpen && previewUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3 sm:p-4"
          onClick={closePreview}
          role="presentation"
        >
          <div
            className="flex h-[min(90vh,920px)] w-full max-w-5xl flex-col overflow-hidden rounded-lg bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label={t("admin.documents.preview.dialog_aria")}
          >
            <div className="flex shrink-0 items-center justify-end border-b border-slate-200 bg-slate-50 px-2 py-1.5">
              <button type="button" className="btn-secondary btn-xs" onClick={closePreview}>
                {t("common.actions.close")}
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-auto bg-slate-100">
              {previewContentType?.includes("pdf") || previewUrl.toLowerCase().endsWith(".pdf") ? (
                <iframe title={t("admin.documents.preview.iframe_title")} src={previewUrl} className="h-full min-h-[70vh] w-full" />
              ) : (
                <img
                  src={previewUrl}
                  alt=""
                  className="mx-auto block h-auto max-h-full min-h-0 w-auto max-w-full object-contain"
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
