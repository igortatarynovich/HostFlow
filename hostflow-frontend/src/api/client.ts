import axios, { AxiosHeaders } from "axios";

const API_BASE_STORAGE_KEY = "hf_api_base";

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
    } else {
      (config.headers as any)["X-Tenant-Id"] = tid;
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

export type OnboardingStatus = {
  business_type: 'agency' | 'employer' | 'services'
  onboarding_required: boolean
  activation_required: boolean
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
export async function listLeads(opts?: { status?: string; stage?: string; limit?: number; offset?: number }) {
  const params: Record<string, any> = {};
  if (opts?.status) params.status = opts.status;
  if (opts?.stage) params.stage = opts.stage;
  if (opts?.limit != null) params.limit = opts.limit;
  if (opts?.offset != null) params.offset = opts.offset;
  const { data } = await api.get(`/leads`, { params });
  return data;
}

export async function updateLeadStage(leadId: string, payload: { stage?: string | null }) {
  const { data } = await api.patch(`/leads/${leadId}`, payload);
  return data;
}

export async function createLeadServiceOrder(leadId: string) {
  const { data } = await api.post(`/leads/${leadId}/service-order`);
  return data;
}

// Invoices ---------------------------------------------------------------
export async function listInvoices(opts?: { company_id?: string; candidate_id?: string; service_order_id?: string; status?: string; limit?: number; offset?: number }) {
  const params: Record<string, any> = {};
  if (opts?.company_id) params.company_id = opts.company_id;
  if (opts?.candidate_id) params.candidate_id = opts.candidate_id;
  if (opts?.service_order_id) params.service_order_id = opts.service_order_id;
  if (opts?.status) params.status = opts.status;
  if (opts?.limit != null) params.limit = opts.limit;
  if (opts?.offset != null) params.offset = opts.offset;
  const { data } = await api.get(`/invoices`, { params });
  return data;
}

export async function getInvoice(id: string) {
  const { data } = await api.get(`/invoices/${id}`);
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

export async function sendInvoice(invoiceId: string) {
  const { data } = await api.post(`/invoices/${invoiceId}/send`);
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
  entityType?: string;
  entityId?: string;
}) {
  const params: Record<string, any> = {};
  if (opts?.status) params.status_filter = opts.status;
  if (opts?.assigneeId) params.assignee_id = opts.assigneeId;
  if (opts?.entityType) params.entity_type = opts.entityType;
  if (opts?.entityId) params.entity_id = opts.entityId;
  const { data } = await api.get(`/reminders`, { params });
  return data;
}

export async function createReminder(payload: Record<string, any>) {
  const { data } = await api.post(`/reminders`, payload);
  return data;
}

export async function updateReminder(id: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/reminders/${id}`, payload);
  return data;
}

export async function completeReminder(id: string) {
  const { data } = await api.post(`/reminders/${id}/complete`);
  return data;
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
  if (opts?.search) params.search = opts.search;
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
