import { api } from "../client";

export type DocumentPolicyScope = "TENANT" | "CLIENT" | "VACANCY";

export interface DocumentPolicy {
  id: string;
  tenant_id: string;
  scope: DocumentPolicyScope;
  scope_id: string | null;
  document_type_id: string;
  enabled: boolean;
  required: boolean;
  alert_days_before_expiry: number | null;
  owner_user_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentPolicyCreate {
  scope: DocumentPolicyScope;
  scope_id?: string | null;
  document_type_id: string;
  enabled?: boolean;
  required?: boolean;
  alert_days_before_expiry?: number | null;
  owner_user_id?: string | null;
  notes?: string | null;
}

export type DocumentPolicyUpdate = DocumentPolicyCreate;

export interface ListDocumentPoliciesOptions {
  scope?: DocumentPolicyScope;
  scope_id?: string;
  document_type_id?: string;
}

// Helper to normalize scope from backend (lowercase) to frontend (uppercase)
function normalizeScope(scope: string): DocumentPolicyScope {
  const upper = scope.toUpperCase();
  if (upper === 'TENANT' || upper === 'CLIENT' || upper === 'VACANCY') {
    return upper as DocumentPolicyScope;
  }
  return 'TENANT'; // fallback
}

export async function listDocumentPolicies(
  options?: ListDocumentPoliciesOptions
): Promise<DocumentPolicy[]> {
  const params: Record<string, string> = {};
  if (options?.scope) {
    // Convert to lowercase to match backend enum values
    params.scope = options.scope.toLowerCase();
  }
  if (options?.scope_id) params.scope_id = options.scope_id;
  if (options?.document_type_id) params.document_type_id = options.document_type_id;

  const { data } = await api.get<any[]>("/document-policies", { params });
  // Normalize scope values from backend (lowercase) to frontend (uppercase)
  return data.map((item) => ({
    ...item,
    scope: normalizeScope(item.scope),
  }));
}

export async function getDocumentPolicy(policyId: string): Promise<DocumentPolicy> {
  const { data } = await api.get<any>(`/document-policies/${policyId}`);
  // Normalize scope value from backend (lowercase) to frontend (uppercase)
  return {
    ...data,
    scope: normalizeScope(data.scope),
  };
}

export async function createDocumentPolicy(
  payload: DocumentPolicyCreate
): Promise<DocumentPolicy> {
  // Convert scope to lowercase to match backend enum values
  const normalizedPayload = {
    ...payload,
    scope: payload.scope.toLowerCase(),
  };
  const { data } = await api.post<any>("/document-policies", normalizedPayload);
  // Normalize scope value from backend (lowercase) to frontend (uppercase)
  return {
    ...data,
    scope: normalizeScope(data.scope),
  };
}

export async function updateDocumentPolicy(
  policyId: string,
  payload: DocumentPolicyUpdate
): Promise<DocumentPolicy> {
  // Convert scope to lowercase to match backend enum values
  const normalizedPayload = payload.scope
    ? {
        ...payload,
        scope: payload.scope.toLowerCase(),
      }
    : payload;
  const { data } = await api.patch<any>(`/document-policies/${policyId}`, normalizedPayload);
  // Normalize scope value from backend (lowercase) to frontend (uppercase)
  return {
    ...data,
    scope: normalizeScope(data.scope),
  };
}

export async function deleteDocumentPolicy(policyId: string): Promise<void> {
  await api.delete(`/document-policies/${policyId}`);
}
