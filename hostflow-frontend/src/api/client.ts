import axios, { AxiosHeaders } from "axios";
import type { Lead } from "./types";

const API_BASE_STORAGE_KEY = "hf_api_base";
export const OWN_COMPANY_STORAGE_KEY = "hf_own_company_id";
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function safeStorageGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeStorageSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // ignore storage failures (private mode, etc.)
  }
}

function safeStorageRemove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // ignore
  }
}

function stripTrailingSlash(url: string): string {
  return url.replace(/\/+$/, "");
}

function isLocalHost(hostname: string): boolean {
  return (
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname.endsWith(".local") ||
    hostname.startsWith("192.168.") ||
    hostname.startsWith("10.") ||
    hostname.startsWith("172.16.") ||
    hostname.startsWith("172.17.") ||
    hostname.startsWith("172.18.") ||
    hostname.startsWith("172.19.") ||
    hostname.startsWith("172.2") // covers 172.20 – 172.29
  );
}

function normalizeApiBase(input: string): string | null {
  const trimmed = (input || "").trim();
  if (!trimmed) return null;

  const ensureAbsolute = (value: string): string | null => {
    try {
      return stripTrailingSlash(new URL(value).toString());
    } catch {
      return null;
    }
  };

  if (/^https?:\/\//i.test(trimmed)) {
    return ensureAbsolute(trimmed);
  }

  if (trimmed.startsWith("//") && typeof window !== "undefined" && window.location) {
    return ensureAbsolute(`${window.location.protocol}${trimmed}`);
  }

  if (trimmed.startsWith("/") && typeof window !== "undefined" && window.location) {
    return ensureAbsolute(new URL(trimmed, window.location.origin).toString());
  }

  // bare host[:port] case — assume http
  return ensureAbsolute(`http://${trimmed}`);
}

function readStoredApiBase(): string | null {
  const stored = safeStorageGet(API_BASE_STORAGE_KEY);
  if (!stored) return null;
  return normalizeApiBase(stored);
}

function persistApiBase(value: string | null): string | null {
  if (!value) {
    safeStorageRemove(API_BASE_STORAGE_KEY);
    return null;
  }
  const normalized = normalizeApiBase(value);
  if (!normalized) {
    safeStorageRemove(API_BASE_STORAGE_KEY);
    return null;
  }
  safeStorageSet(API_BASE_STORAGE_KEY, normalized);
  return normalized;
}

function defaultLocalBase(): string {
  if (typeof window !== "undefined" && window.location) {
    const { protocol, hostname } = window.location;
    const port =
      window.location.port && window.location.port.length > 0
        ? window.location.port
        : protocol === "https:"
        ? "443"
        : "80";
    const inferredPort = isLocalHost(hostname) ? "8000" : port;
    const prefixPort =
      inferredPort === "80" && protocol === "http:"
        ? ""
        : inferredPort === "443" && protocol === "https:"
        ? ""
        : `:${inferredPort}`;
    return stripTrailingSlash(`${protocol}//${hostname}${prefixPort}/api/v1`);
  }
  return "http://localhost:8000/api/v1";
}

export function resolveApiBase(): string {
  const stored = readStoredApiBase();
  if (stored) return stored;

  const rawEnv = (import.meta.env.VITE_API_URL ?? import.meta.env.VITE_API_BASE) as string | undefined;
  let envUrl: URL | null = null;
  if (rawEnv && typeof rawEnv === "string") {
    const candidate = normalizeApiBase(rawEnv);
    if (candidate) {
      try {
        envUrl = new URL(candidate);
      } catch {
        envUrl = null;
      }
    }
  }

  const globalOverride =
    typeof window !== "undefined" && (window as any).__HOSTFLOW_API_BASE__
      ? normalizeApiBase((window as any).__HOSTFLOW_API_BASE__)
      : null;
  if (globalOverride) {
    return globalOverride;
  }

  if (typeof window !== "undefined" && window.location) {
    const { hostname } = window.location;
    const localHost = isLocalHost(hostname);

    if (localHost) {
      if (envUrl) {
        const envHostIsLocal = isLocalHost(envUrl.hostname);
        if (!envHostIsLocal) {
          // Игнорируем продовый URL, если фронт запущен локально
          return defaultLocalBase();
        }
        return stripTrailingSlash(envUrl.toString());
      }
      return defaultLocalBase();
    }

    if (!envUrl) {
      return stripTrailingSlash(`${window.location.origin.replace(/\/+$/, "")}/api/v1`);
    }
    return stripTrailingSlash(envUrl.toString());
  }

  return stripTrailingSlash(envUrl?.toString() ?? "http://localhost:8000/api/v1");
}

export const apiBaseSettings = {
  get(): string | null {
    return readStoredApiBase();
  },
  set(value: string | null): string | null {
    return persistApiBase(value);
  },
  clear(): void {
    safeStorageRemove(API_BASE_STORAGE_KEY);
  },
};

const DEFAULT_BASE = resolveApiBase();

const DEFAULT_DOCS_BASE =
  import.meta.env.VITE_DOCS_ORIGIN ?? `${DEFAULT_BASE}/db`; // важное: доки ходят на свой origin; по умолчанию /db

export const DEFAULT_TENANT =
  import.meta.env.VITE_TENANT_ID ?? "11111111-1111-1111-1111-111111111111";

export function resolveAssetUrl(path?: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path) || path.startsWith("data:")) {
    return path;
  }
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const needsApiPrefix = normalized.startsWith("/uploads/");
  const withApiPrefix = needsApiPrefix ? `/api${normalized}` : normalized;

  const canUseWindowOrigin =
    typeof window !== "undefined" &&
    window.location &&
    window.location.origin &&
    !import.meta.env?.DEV;

  if (canUseWindowOrigin) {
    return `${window.location.origin}${withApiPrefix}`;
  }

  const base = resolveApiBase();
  try {
    const parsed = new URL(base);
    return `${parsed.protocol}//${parsed.host}${normalized}`;
  } catch {
    try {
      if (typeof window !== "undefined") {
        const resolved = new URL(base, window.location.origin);
        return `${resolved.protocol}//${resolved.host}${withApiPrefix}`;
      }
    } catch {
      /* ignore */
    }
  }

  try {
    if (typeof window !== "undefined" && window.location?.origin) {
      return `${window.location.origin}${withApiPrefix}`;
    }
  } catch {
    /* ignore */
  }
  return normalized;
}

// --- settings used in UI (Sidebar.tsx expects .get/.set)
function sanitizeTenantId(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const first = String(raw).split(",")[0].trim();
  if (!first) return null;
  return first;
}

function sanitizeOwnCompanyId(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const first = String(raw).split(",")[0].trim();
  if (!first) return null;
  return UUID_RE.test(first) ? first : null;
}

export const settings = {
  get(): string {
    const keys = ["tenant_id", "X-Tenant-Id", "x-tenant-id"];
    let value: string | null = null;
    for (const key of keys) {
      const raw = safeStorageGet(key);
      const sanitized = sanitizeTenantId(raw);
      if (sanitized && raw !== sanitized) {
        safeStorageSet(key, sanitized);
      }
      if (!value && sanitized) {
        value = sanitized;
      }
    }
    if (!value) {
      value = DEFAULT_TENANT;
    }
    return value || DEFAULT_TENANT;
  },
  set(value: string) {
    const sanitized = sanitizeTenantId(value) ?? DEFAULT_TENANT;
    safeStorageSet("tenant_id", sanitized);
    safeStorageSet("X-Tenant-Id", sanitized);
    safeStorageSet("x-tenant-id", sanitized);
  },
};

export const ownCompanySettings = {
  get(): string | null {
    const stored = safeStorageGet(OWN_COMPANY_STORAGE_KEY);
    const sanitized = sanitizeOwnCompanyId(stored);
    if (sanitized && stored !== sanitized) {
      safeStorageSet(OWN_COMPANY_STORAGE_KEY, sanitized);
    }
    return sanitized;
  },
  set(value: string | null) {
    const trimmed = sanitizeOwnCompanyId(value) ?? "";
    if (!trimmed) safeStorageRemove(OWN_COMPANY_STORAGE_KEY);
    else safeStorageSet(OWN_COMPANY_STORAGE_KEY, trimmed);
    try {
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("hf:own-company-changed", { detail: { id: trimmed || null } }),
        );
      }
    } catch {
      // ignore
    }
  },
};

// --- helper to attach headers
function attachInterceptors(inst: ReturnType<typeof axios.create>, tenantId?: string) {
  inst.interceptors.request.use((config) => {
    const tid = tenantId ?? settings.get();

    // ensure default headers
    if (!config.headers) config.headers = new AxiosHeaders();
    if (config.headers instanceof AxiosHeaders) {
      if (!config.headers.has("Accept")) config.headers.set("Accept", "application/json");
    } else {
      (config.headers as any)["Accept"] = (config.headers as any)["Accept"] || "application/json";
    }
    // set JSON content type on write operations if not provided
    const method = (config.method || "get").toLowerCase();
    const isWrite = method === "post" || method === "put" || method === "patch";
    if (isWrite) {
      if (config.headers instanceof AxiosHeaders) {
        if (!config.headers.has("Content-Type")) config.headers.set("Content-Type", "application/json");
      } else {
        (config.headers as any)["Content-Type"] = (config.headers as any)["Content-Type"] || "application/json";
      }
    }

    if (!config.headers) config.headers = new AxiosHeaders();
    if (config.headers instanceof AxiosHeaders) {
      config.headers.set("X-Tenant-Id", tid);
      const ownId = ownCompanySettings.get();
      if (ownId) config.headers.set("X-Own-Company-Id", ownId);
    } else {
      (config.headers as any)["X-Tenant-Id"] = tid;
      const ownId = ownCompanySettings.get();
      if (ownId) (config.headers as any)["X-Own-Company-Id"] = ownId;
    }

    const token =
      safeStorageGet("access_token") ||
      safeStorageGet("accessToken") ||
      safeStorageGet("token") ||
      null;
    if (token) {
      if (config.headers instanceof AxiosHeaders) {
        config.headers.set("Authorization", `Bearer ${token}`);
      } else {
        (config.headers as any).Authorization = `Bearer ${token}`;
      }
    }

    return config;
  });
}

// --- base axios instances
const apiInstance = axios.create({ baseURL: DEFAULT_BASE, withCredentials: true });
attachInterceptors(apiInstance);

// отдельный клиент для сервиса документов (другой origin/baseURL!)
const docsApiInstance = axios.create({ baseURL: DEFAULT_DOCS_BASE, withCredentials: true });
attachInterceptors(docsApiInstance);

// helper for auth code
export function setToken(token: string | null) {
  if (token) {
    safeStorageSet("token", token);
    safeStorageSet("access_token", token);
  } else {
    safeStorageRemove("token");
    safeStorageRemove("access_token");
  }
}

/** --- Backward-compat named exports --- */
export const api = apiInstance;
export const docsApi = docsApiInstance;

// legacy: some files import { withTenant } from "./client"
// теперь аргумент tenantId опционален
export function withTenant(tenantId?: string) {
  const id = tenantId ?? settings.get();
  const inst = axios.create({ baseURL: DEFAULT_BASE, withCredentials: true });
  attachInterceptors(inst, id);
  return inst;
}

// ---- Documents API helpers -------------------------------------------------
export type DocDecision = "approved" | "rejected";

/**
 * List candidate documents.
 */
export async function listCandidateDocuments(
  ownerId: string,
  opts?: { includeLastCheck?: boolean; limit?: number; offset?: number; tenantId?: string }
) {
  const tenant = opts?.tenantId ?? settings.get();
  const params: Record<string, any> = { tenant_id: tenant };
  if (opts?.includeLastCheck) params.include_last_check = true;
  if (opts?.limit != null) params.limit = opts.limit;
  if (opts?.offset != null) params.offset = opts.offset;

  const { data } = await docsApi.get(`/candidate/${ownerId}/documents`, { params });
  return data;
}

/**
 * Fetch a single document (optionally with checks).
 */
export async function getDocument(
  docId: string,
  opts?: { includeChecks?: boolean }
) {
  const params: Record<string, any> = {};
  if (opts?.includeChecks) params.include_checks = true;

  const { data } = await docsApi.get(`/documents/${docId}`, { params });
  return data;
}

/**
 * Create a candidate document (JSON payload).
 */
export async function createCandidateDocument(
  ownerId: string,
  payload: {
    type_code: string;
    title?: string;
    issued_at?: string;
    expires_at?: string;
    meta_json?: any;
    owner_type?: "candidate";
    owner_id?: string;
    tenant_id?: string;
  }
) {
  const body = {
    owner_type: "candidate" as const,
    owner_id: ownerId,
    tenant_id: payload.tenant_id ?? settings.get(),
    ...payload,
  };
  const { data } = await docsApi.post(`/candidate/${ownerId}/documents`, body);
  return data;
}

/**
 * Add a check (approve/reject) to a document.
 */
export async function checkDocument(docId: string, input: {
  reviewer_id: string;
  decision: DocDecision;
  reason_code?: string | null;
  comment?: string | null;
}) {
  const { data } = await docsApi.post(`/documents/${docId}/check`, input);
  return data;
}

/**
 * Get presigned upload info for a document.
 */
export async function presignUpload(docId: string) {
  const { data } = await docsApi.post(`/documents/${docId}/presign-upload`);
  return data as { url: string; method: string; fields: Record<string, string> };
}

/**
 * Summary and checklist helpers.
 */
export async function getSummary(ownerId: string, tenantId?: string) {
  const tenant = tenantId ?? settings.get();
  const { data } = await docsApi.get(`/candidate/${ownerId}/documents/summary`, {
    params: { tenant_id: tenant },
  });
  return data;
}

export async function getChecklist(ownerId: string, tenantId?: string) {
  const tenant = tenantId ?? settings.get();
  const { data } = await docsApi.get(`/candidate/${ownerId}/checklist`, {
    params: { tenant_id: tenant },
  });
  return data;
}

/**
 * Exports
 */
export async function exportDocumentsJSON(ownerId: string, tenantId?: string) {
  const tenant = tenantId ?? settings.get();
  const { data } = await docsApi.get(`/candidate/${ownerId}/documents/export.json`, {
    params: { tenant_id: tenant },
  });
  return data;
}

export async function exportDocumentsCSV(ownerId: string, tenantId?: string) {
  const tenant = tenantId ?? settings.get();
  const res = await docsApi.get(`/candidate/${ownerId}/documents/export.csv`, {
    params: { tenant_id: tenant },
    responseType: "blob",
  });
  return res.data;
}

// ---- Core app API helpers (companies, vacancies, catalogs) -----------------

// Companies ---------------------------------------------------------------
export async function listCompanies(opts?: { limit?: number; offset?: number; search?: string; tenantId?: string }) {
  const params: Record<string, any> = {};
  if (opts?.limit != null) params.limit = opts.limit;
  if (opts?.offset != null) params.offset = opts.offset;
  if (opts?.search) {
    params.q = opts.search;
    params.search = opts.search;
  }
  const client = opts?.tenantId ? withTenant(opts.tenantId) : api;
  const { data } = await client.get(`/companies/`, { params });
  return data;
}

export async function getCompany(id: string) {
  const { data } = await api.get(`/companies/${id}`);
  return data;
}

export async function createCompany(payload: Record<string, any>) {
  const { data } = await api.post(`/companies/`, payload);
  return data;
}

// Own companies (legal entities within tenant) --------------------------------
export type OwnCompanyRecord = {
  id: string
  tenant_id: string
  name: string
  onboarding_demo?: {
    entity?: string
    pipeline_total?: number
    need_action?: number
    stuck?: number
    active_today?: number
  } | null
  legal_name?: string | null
  tax_id?: string | null
  phone?: string | null
  email?: string | null
  website?: string | null
  country_code?: string | null
  country?: string | null
  city?: string | null
  address?: string | null
  notes?: string | null
  is_archived?: boolean | null
  contacts?: Record<string, any>
  extra?: Record<string, any>
  bank_details?: Record<string, any>
  created_at?: string | null
  updated_at?: string | null
}

export async function listOwnCompanies() {
  try {
    const { data } = await api.get<{ items: OwnCompanyRecord[]; active_own_company_id?: string | null }>(`/own-companies`)
    return data
  } catch (e: any) {
    if (e?.response?.status === 404) {
      const { data } = await api.get<{ items: OwnCompanyRecord[]; active_own_company_id?: string | null }>(`/own_companies`)
      return data
    }
    throw e
  }
}

export type OwnCompanyCreatePayload = Partial<OwnCompanyRecord> & {
  name: string
  business_type?: 'agency' | 'employer' | 'services'
  industry?: string
  team_size?: string
  workspace_name?: string
  workspace_count?: number
  working_hours_preset?: string
}

export async function createOwnCompany(payload: OwnCompanyCreatePayload) {
  try {
    const { data } = await api.post<OwnCompanyRecord>(`/own-companies`, payload)
    return data
  } catch (e: any) {
    if (e?.response?.status === 404) {
      const { data } = await api.post<OwnCompanyRecord>(`/own_companies`, payload)
      return data
    }
    throw e
  }
}

export async function setActiveOwnCompany(ownCompanyId: string) {
  let data: { items: OwnCompanyRecord[]; active_own_company_id?: string | null }
  try {
    const res = await api.post<{ items: OwnCompanyRecord[]; active_own_company_id?: string | null }>(`/own-companies/active`, {
      own_company_id: ownCompanyId,
    })
    data = res.data
  } catch (e: any) {
    if (e?.response?.status === 404) {
      const res = await api.post<{ items: OwnCompanyRecord[]; active_own_company_id?: string | null }>(`/own_companies/active`, {
        own_company_id: ownCompanyId,
      })
      data = res.data
    } else {
      throw e
    }
  }
  try {
    ownCompanySettings.set(ownCompanyId)
  } catch {
    // ignore
  }
  return data
}

export async function createClientCompany(payload: Record<string, any>) {
  const body = { ...payload, company_role: payload.company_role ?? 'client' };
  const { data } = await api.post(`/companies/`, body);
  return data;
}

export type OnboardingStatus = {
  business_type: 'agency' | 'employer' | 'services'
  onboarding_required: boolean
  activation_required: boolean
  demo_seeded?: boolean
  companies_count: number
  leads_count: number
  vacancies_count: number
  service_orders_count: number
  reminders_count: number
  clients_count: number
  counterparties_count: number
  steps: {
    company_created: boolean
    first_lead_created: boolean
    first_vacancy_created: boolean
    first_service_order_created: boolean
    first_client_created: boolean
    next_action_created: boolean
  }
};

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  const { data } = await api.get<OnboardingStatus>('/onboarding/status');
  return data;
}

export type OnboardingClearDemoResult = {
  reminders: number
  leads: number
  candidates: number
  companies: number
}

export async function clearOnboardingDemoData(): Promise<OnboardingClearDemoResult> {
  const { data } = await api.post<OnboardingClearDemoResult>('/onboarding/clear-demo-data');
  return data;
}

export async function updateCompany(id: string, payload: Record<string, any>) {
  const { data } = await api.put(`/companies/${id}`, payload);
  return data;
}

export async function updateCompanyLegal(id: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/companies/${id}/legal`, payload);
  return data;
}

export async function replaceCompanyBilling(id: string, payload: Record<string, any>) {
  const { data } = await api.put(`/companies/${id}/billing`, payload);
  return data;
}

export async function addCompanyBankAccount(id: string, payload: Record<string, any>) {
  const { data } = await api.post(`/companies/${id}/bank-accounts`, payload);
  return data;
}

export async function updateCompanyBankAccount(id: string, accountId: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/companies/${id}/bank-accounts/${accountId}`, payload);
  return data;
}

export async function deleteCompanyBankAccount(id: string, accountId: string) {
  await api.delete(`/companies/${id}/bank-accounts/${accountId}`);
}

export async function addCompanyContact(id: string, payload: Record<string, any>) {
  const { data } = await api.post(`/companies/${id}/contacts`, payload);
  return data;
}

export async function updateCompanyContact(id: string, contactId: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/companies/${id}/contacts/${contactId}`, payload);
  return data;
}

export async function deleteCompanyContact(id: string, contactId: string) {
  await api.delete(`/companies/${id}/contacts/${contactId}`);
}

export async function replaceCompanyOperations(id: string, payload: Record<string, any>) {
  const { data } = await api.put(`/companies/${id}/operations`, payload);
  return data;
}

export async function updateCompanyCompliance(id: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/companies/${id}/compliance`, payload);
  return data;
}

export async function updateCompanyPortal(id: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/companies/${id}/portal`, payload);
  return data;
}

export async function enableCompanyPortal(id: string, payload: { enabled: boolean; url?: string }) {
  const { data } = await api.post(`/companies/${id}/enable-portal`, payload);
  return data;
}

export async function updateCompanyIntegrations(id: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/companies/${id}/integrations`, payload);
  return data;
}

export async function getCompanyReadiness(id: string) {
  const { data } = await api.get(`/companies/${id}/readiness`);
  return data;
}

// Leads -----------------------------------------------------------------
export async function listLeads(opts?: {
  status?: string;
  stage?: string;
  nextAction?: string;
  /** Substring search (server applies when trimmed length ≥ 2). */
  q?: string;
  customFieldKey?: string;
  /** Sent when customFieldKey is set; use empty string to match blank stored values. */
  customFieldValue?: string;
  limit?: number;
  offset?: number;
}) {
  const params: Record<string, any> = {};
  if (opts?.status) params.status = opts.status;
  if (opts?.stage) params.stage = opts.stage;
  if (opts?.nextAction) params.next_action = opts.nextAction;
  const qq = (opts?.q || '').trim();
  if (qq.length >= 2) params.q = qq;
  const cfk = (opts?.customFieldKey || '').trim();
  if (cfk) {
    params.custom_field_key = cfk;
    params.custom_field_value = opts?.customFieldValue ?? '';
  }
  if (opts?.limit != null) params.limit = opts.limit;
  if (opts?.offset != null) params.offset = opts.offset;
  const { data } = await api.get(`/leads`, { params });
  return data;
}

export async function getLead(leadId: string): Promise<Lead> {
  const { data } = await api.get<Lead>(`/leads/${leadId}`);
  return data;
}

export async function getLeadTimeline(leadId: string) {
  const { data } = await api.get(`/leads/${leadId}/timeline`);
  return data;
}

export async function updateLeadStage(leadId: string, payload: {
  stage?: string | null
  assignment_locked?: boolean
  lost_reason_code?: string
  lost_reason_note?: string
}) {
  const { data } = await api.patch(`/leads/${leadId}`, payload);
  return data;
}

export async function bulkUpdateLeads(payload: {
  lead_ids: string[];
  stage?: string | null;
  status?: string | null;
  lost_reason_code?: string;
  lost_reason_note?: string;
}) {
  const { data } = await api.patch(`/leads/bulk`, payload);
  return data;
}

export type BulkAutoProcessQueueItem = {
  lead_id: string
  ok: boolean
  status_after?: string | null
  error?: string | null
}

export type BulkAutoProcessQueueResponse = {
  results: BulkAutoProcessQueueItem[]
  attempted: number
  succeeded: number
  failed: number
}

/** §2.3 Team+ gated: batch Meta process for needs_routing / failed leads. */
export async function bulkAutoProcessLeadQueue(payload?: { max_items?: number }) {
  const { data } = await api.post<BulkAutoProcessQueueResponse>(`/leads/bulk/auto-process-queue`, payload ?? {})
  return data
}

/** §2.10 NBA: Team+ gated batch Meta process for status=new (FIFO). */
export async function bulkProcessNewMetaLeads(payload?: { max_items?: number }) {
  const { data } = await api.post<BulkAutoProcessQueueResponse>(`/leads/bulk/process-new-queue`, payload ?? {})
  return data
}

export async function createLeadServiceOrder(leadId: string) {
  const { data } = await api.post(`/leads/${leadId}/service-order`);
  return data;
}

export async function processLead(leadId: string) {
  const { data } = await api.post(`/leads/${leadId}/process`);
  return data;
}

// Invoices ---------------------------------------------------------------
export async function listInvoices(opts?: {
  company_id?: string;
  candidate_id?: string;
  service_order_id?: string;
  status?: string;
  unpaid?: boolean;
  q?: string;
  limit?: number;
  offset?: number;
}) {
  const params: Record<string, any> = {};
  if (opts?.company_id) params.company_id = opts.company_id;
  if (opts?.candidate_id) params.candidate_id = opts.candidate_id;
  if (opts?.service_order_id) params.service_order_id = opts.service_order_id;
  if (opts?.status) params.status = opts.status;
  if (opts?.unpaid) params.unpaid = true;
  if (opts?.q) params.q = opts.q;
  if (opts?.limit != null) params.limit = opts.limit;
  if (opts?.offset != null) params.offset = opts.offset;
  const { data } = await api.get(`/invoices`, { params });
  return data;
}

export async function getInvoice(id: string) {
  const { data } = await api.get(`/invoices/${id}`);
  return data;
}

export async function getInvoiceCorrectionChain(id: string) {
  const { data } = await api.get(`/invoices/${id}/chain`);
  return data;
}

export async function getInvoiceActivity(id: string, opts?: { limit?: number }) {
  const params: Record<string, any> = {};
  if (opts?.limit != null) params.limit = opts.limit;
  const { data } = await api.get(`/invoices/${id}/activity`, { params });
  return data;
}

export async function createInvoice(payload: Record<string, any>) {
  const { data } = await api.post(`/invoices`, payload);
  return data;
}

export async function createInvoiceFromServiceOrder(orderId: string) {
  const { data } = await api.post(`/invoices/from-service-order/${orderId}`);
  return data;
}

export async function listInvoicesByServiceOrders(orderIds: string[]) {
  const params: Record<string, any> = {}
  const clean = (orderIds || []).map((x) => String(x || '').trim()).filter(Boolean)
  if (clean.length === 0) return []
  params.order_id = clean
  const { data } = await api.get(`/invoices/service-orders-summary`, { params })
  return data as Array<{
    service_order_id: string
    invoice_id: string
    invoice_number: string
    status: string
    total_amount: number
    paid_amount: number
    due_date?: string | null
  }>
}

export async function updateInvoice(id: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/invoices/${id}`, payload);
  return data;
}

export async function createPayment(invoiceId: string, payload: Record<string, any>) {
  const { data } = await api.post(`/invoices/${invoiceId}/payments`, payload);
  return data;
}

export async function createRefund(paymentId: string, payload: Record<string, any>) {
  const { data } = await api.post(`/invoices/payments/${paymentId}/refunds`, payload);
  return data;
}

export async function sendInvoice(invoiceId: string, payload?: { recipient_email?: string; subject?: string; body?: string }) {
  const { data } = await api.post(`/invoices/${invoiceId}/send`, payload ?? {});
  return data;
}

export async function cancelInvoice(invoiceId: string) {
  const { data } = await api.post(`/invoices/${invoiceId}/cancel`);
  return data;
}

export async function getInvoicePdf(invoiceId: string): Promise<Blob> {
  const { data } = await api.get(`/invoices/${invoiceId}/pdf`, { responseType: 'blob' });
  return data;
}

// Notifications ---------------------------------------------------------------
export async function listNotifications(opts?: { limit?: number; includeRead?: boolean; scope?: 'all' | 'direct' }) {
  const params: Record<string, any> = {};
  if (opts?.limit != null) params.limit = opts.limit;
  if (opts?.includeRead) params.include_read = true;
  if (opts?.scope) params.scope = opts.scope;
  const { data } = await api.get(`/notifications`, { params });
  return data;
}

export async function markNotificationsRead(payload: { ids?: string[]; markAll?: boolean }) {
  const body: Record<string, any> = {};
  if (payload.ids && payload.ids.length > 0) body.ids = payload.ids;
  if (payload.markAll) body.mark_all = true;
  if (!body.ids && !body.mark_all) {
    body.mark_all = true;
  }
  await api.post(`/notifications/read`, body);
}

export async function reconcileNotifications() {
  const { data } = await api.post(`/notifications/reconcile`, {});
  return data as { cleaned: number };
}

export async function reconcileTenantNotifications(maxUsers = 2000) {
  const { data } = await api.post(`/notifications/reconcile-tenant`, null, {
    params: { max_users: maxUsers },
  });
  return data as { users_processed: number; cleaned: number };
}

// Reminders v2 ---------------------------------------------------------------
export async function listReminders(opts?: {
  status?: string[];
  assigneeId?: string;
  assigneeScope?: 'mine' | 'team';
  entityType?: string;
  entityId?: string;
  types?: string[];
  dueFrom?: string | Date;
  dueTo?: string | Date;
  /** Substring match on title, description, or message (backend; uses assignee scope). */
  q?: string;
  limit?: number;
  signal?: AbortSignal;
}) {
  const params: Record<string, any> = {};
  if (opts?.status) params.status_filter = opts.status;
  if (opts?.types) params.type_filter = opts.types;
  if (opts?.assigneeId) params.assignee_id = opts.assigneeId;
  if (opts?.assigneeScope) params.assignee_scope = opts.assigneeScope;
  if (opts?.entityType) params.entity_type = opts.entityType;
  if (opts?.entityId) params.entity_id = opts.entityId;
  if (opts?.dueFrom) params.due_from = opts.dueFrom;
  if (opts?.dueTo) params.due_to = opts.dueTo;
  if (opts?.q) params.q = opts.q;
  if (opts?.limit != null) params.limit = opts.limit;
  const { data } = await api.get(`/reminders`, { params, signal: opts?.signal });
  return data;
}

export async function createReminder(payload: Record<string, any>) {
  const { data } = await api.post(`/reminders`, payload);
  return data;
}

export type BulkReminderCreateResultItem = {
  entity_id: string
  ok: boolean
  reminder_id?: string | null
  error?: string | null
}

export type BulkReminderCreateResponse = {
  results: BulkReminderCreateResultItem[]
}

export async function createBulkReminders(payload: {
  title: string
  description?: string
  type?: string
  entity_type: string
  entity_ids: string[]
  due_at: string | Date
  remind_at?: string | Date
  priority?: string
  assignee_id?: string
  source?: string
  channel?: string
  payload?: Record<string, unknown>
}): Promise<BulkReminderCreateResponse> {
  const { data } = await api.post<BulkReminderCreateResponse>(`/reminders/bulk`, payload)
  return data
}

export async function updateReminder(id: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/reminders/${id}`, payload);
  return data;
}

export async function completeReminder(id: string) {
  const { data } = await api.post(`/reminders/${id}/complete`);
  return data;
}

// Activities v1 --------------------------------------------------------------
export async function listActivities(opts?: {
  status?: string[];
  assigneeId?: string;
  assigneeScope?: 'mine' | 'team';
  entityType?: string;
  entityId?: string;
  types?: string[];
  dueFrom?: string | Date;
  dueTo?: string | Date;
}) {
  const params: Record<string, any> = {};
  if (opts?.status) params.status_filter = opts.status;
  if (opts?.types) params.type_filter = opts.types;
  if (opts?.assigneeId) params.assignee_id = opts.assigneeId;
  if (opts?.assigneeScope) params.assignee_scope = opts.assigneeScope;
  if (opts?.entityType) params.entity_type = opts.entityType;
  if (opts?.entityId) params.entity_id = opts.entityId;
  if (opts?.dueFrom) params.due_from = opts.dueFrom;
  if (opts?.dueTo) params.due_to = opts.dueTo;
  const { data } = await api.get(`/activities`, { params });
  return data;
}

export async function createActivity(payload: Record<string, any>) {
  const { data } = await api.post(`/activities`, payload);
  return data;
}

export async function updateActivity(id: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/activities/${id}`, payload);
  return data;
}

export async function completeActivity(id: string) {
  const { data } = await api.post(`/activities/${id}/complete`);
  return data;
}

export async function snoozeActivity(id: string, payload: { minutes?: number; new_remind_at?: string | Date }) {
  const body: Record<string, any> = {};
  if (payload.minutes != null) body.minutes = payload.minutes;
  if (payload.new_remind_at) body.new_remind_at = payload.new_remind_at;
  const { data } = await api.post(`/activities/${id}/snooze`, body);
  return data;
}

export async function createBulkActivities(payload: {
  title: string
  description?: string
  type?: string
  entity_type: string
  entity_ids: string[]
  due_at: string | Date
  remind_at?: string | Date
  duration_minutes?: number
  source?: string
  priority?: string
}) {
  const { data } = await api.post(`/activities/bulk`, payload)
  return data
}

// Candidates (operational views) --------------------------------------------
export async function listCandidatesNoNextAction(opts?: {
  limit?: number
  offset?: number
  stages?: string[]
  managerId?: string
  assigneeId?: string
  scopeTenantId?: string
}) {
  const params: Record<string, any> = {}
  if (opts?.limit != null) params.limit = opts.limit
  if (opts?.offset != null) params.offset = opts.offset
  if (opts?.stages && opts.stages.length) params.stages = opts.stages
  if (opts?.managerId) params.manager_id = opts.managerId
  if (opts?.assigneeId) params.assignee_id = opts.assigneeId
  if (opts?.scopeTenantId) params.scope_tenant_id = opts.scopeTenantId
  const { data } = await api.get(`/candidates/no-next-action`, { params })
  return data
}

export async function getCandidateTimeline(candidateId: string) {
  const { data } = await api.get(`/candidates/${candidateId}/timeline`)
  return data
}

/** R1.5 Phase D: single bundle for list work panel (profile + reminders + timeline + comms links). */
export async function getCandidateWorkPanel(
  candidateId: string,
  opts?: { timelineLimit?: number; assigneeScope?: 'mine' | 'team' },
) {
  const params: Record<string, unknown> = {}
  if (opts?.timelineLimit != null) params.timeline_limit = opts.timelineLimit
  if (opts?.assigneeScope) params.assignee_scope = opts.assigneeScope
  const { data } = await api.get(`/candidates/${candidateId}/work-panel`, {
    params: Object.keys(params).length ? params : undefined,
  })
  return data
}

export async function getCandidateChangeLog(candidateId: string, opts?: { limit?: number }) {
  const params: Record<string, any> = {}
  if (opts?.limit != null) params.limit = opts.limit
  const { data } = await api.get(`/candidates/${candidateId}/change-log`, { params })
  return data
}

export async function snoozeReminder(id: string, payload: { minutes?: number; new_remind_at?: string | Date }) {
  const body: Record<string, any> = {};
  if (payload.minutes != null) body.minutes = payload.minutes;
  if (payload.new_remind_at) body.new_remind_at = payload.new_remind_at;
  const { data } = await api.post(`/reminders/${id}/snooze`, body);
  return data;
}

// Vacancies ---------------------------------------------------------------
export async function listVacancies(opts?: { limit?: number; offset?: number; search?: string }) {
  const params: Record<string, any> = {};
  if (opts?.limit != null) params.limit = opts.limit;
  if (opts?.offset != null) params.offset = opts.offset;
  if (opts?.search) {
    params.q = opts.search;
  }
  const { data } = await api.get(`/vacancies/`, { params });
  return data;
}

export async function getVacancy(id: string) {
  const { data } = await api.get(`/vacancies/${id}`);
  return data;
}

export async function createVacancy(payload: Record<string, any>) {
  const { data } = await api.post(`/vacancies/`, payload);
  return data;
}

export async function updateVacancy(id: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/vacancies/${id}`, payload);
  return data;
}

// Catalogs ----------------------------------------------------------------
export async function listManagers() {
  const { data } = await api.get(`/catalogs/managers`);
  return data as Array<{
    id: string;
    short_id?: string | null;
    full_name?: string | null;
    email: string;
    label: string;
  }>;
}
// Keep the default export of the main API instance
export default apiInstance;
