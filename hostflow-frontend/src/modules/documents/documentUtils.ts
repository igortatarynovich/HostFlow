/**
 * Utility functions for document management
 */

import { docsApi } from "../../api/client";
import {
  MAX_FILE_BYTES,
  DOCUMENT_STATUS_META,
  EXPIRING_SOON_THRESHOLD_DAYS,
  READINESS_TO_STATUS,
  STATUS_FROM_RANK,
  CORE_METADATA_FIELDS,
  DOC_TYPE_CODE_ALIASES,
} from "./constants";
import type { Document, DocumentStatus } from "../../api/types";
import type { MetadataFieldConfig, MetadataState } from "./types";

export const toArray = <T,>(value: any): T[] => {
  if (Array.isArray(value)) return value as T[];
  if (Array.isArray(value?.items)) return value.items as T[];
  if (Array.isArray(value?.data)) return value.data as T[];
  return [];
};

export const isTooLarge = (file?: File | null) => !!file && file.size > MAX_FILE_BYTES;

export const formatDate = (value?: string | null) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString();
};

export const formatDateTime = (value?: string | null) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
};

export const dateValue = (value?: string | null) => {
  if (!value) return 0;
  const time = Date.parse(value);
  return Number.isNaN(time) ? 0 : time;
};

export const daysUntil = (value?: string | null) => {
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

export const resolveDocumentUrl = (link: string): string => {
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

export const guessPreviewable = (contentType: string | null | undefined, filename?: string | null) => {
  const mime = (contentType || "").toLowerCase();
  if (mime.startsWith("image/") || mime === "application/pdf") return true;
  if (filename) {
    const lower = filename.toLowerCase();
    return lower.endsWith(".pdf") || lower.endsWith(".jpg") || lower.endsWith(".jpeg") || lower.endsWith(".png");
  }
  return false;
};

export const detectPreviewMime = (contentType: string | null | undefined, filename?: string | null) => {
  const lowerType = (contentType || "").toLowerCase();
  if (lowerType) return lowerType;
  if (!filename) return null;
  const lower = filename.toLowerCase();
  if (lower.endsWith(".pdf")) return "application/pdf";
  if (lower.endsWith(".png")) return "image/png";
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
  return null;
};

export const filenameFromUrl = (value: string | null | undefined): string | null => {
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

export const isProbablyHtmlBlob = async (blob: Blob, contentType?: string | null): Promise<boolean> => {
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

export const computeTodayIso = (): string => new Date().toISOString().slice(0, 10);

export const normalizeDocTypeCode = (value?: string | null): string => {
  const raw = String(value || "").trim();
  if (!raw) return "";
  return DOC_TYPE_CODE_ALIASES[raw] || raw;
};

export const resolveDocTypeLabel = (
  t: (key: string, opts?: any) => string,
  typeCode: string,
  dbName?: string | null
): string => {
  const normalized = normalizeDocTypeCode(typeCode);
  const key = `admin.documents.type_codes.${normalized}`;
  const translated = t(key, { defaultValue: key });
  if (translated && translated !== key) return translated;
  if (dbName && dbName.trim()) return dbName.trim();
  if (normalized) return normalized.replace(/_/g, " ");
  return "";
};

export const effectiveStatus = (doc: Document): DocumentStatus => {
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
export const normalizeStatus = (value: any): DocumentStatus | null => {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  const matched = /^documentstatus[.:]?(.+)$/i.exec(trimmed);
  const normalized = (matched ? matched[1] : trimmed).toLowerCase();
  return (DOCUMENT_STATUS_META as Record<string, any>)[normalized]
    ? (normalized as DocumentStatus)
    : null;
};

export const primaryStatus = (doc: Document): DocumentStatus => {
  const normalized = normalizeStatus(doc.status);
  if (normalized) return normalized;
  return effectiveStatus(doc);
};

export const resolveRequestedFromDate = (doc: Document): string | null => {
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

export const isExpiringSoonDoc = (doc: Document): boolean => {
  const expiry = doc.expire_date || doc.expires_at;
  const diff = daysUntil(expiry);
  return diff !== null && diff >= 0 && diff <= EXPIRING_SOON_THRESHOLD_DAYS;
};

export const defaultMetadataValue = (field: MetadataFieldConfig) => {
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

export const buildMetadataStateFromDoc = (doc: Document, fields: MetadataFieldConfig[]): MetadataState => {
  const base: MetadataState = {};
  const source = doc.meta_json ?? {};
  fields.forEach((field) => {
    const rawValue =
      source[field.name] !== undefined ? source[field.name] : (doc as Record<string, any>)[field.name];
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
