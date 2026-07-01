import { api, docsApi } from "../client";
import { apiErrorMessage } from "./helpers";

export interface DocumentTemplate {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  documents: Array<{
    doc_type: string;
    kind: string;
    requested_from: string;
    process_type: string;
    required: boolean;
    meta?: Record<string, any>;
    remind_days_before?: number;
  }>;
  created_at: string;
  updated_at: string;
}

export interface ApplyTemplatePayload {
  template_id?: string;
  template_code?: string;
}

export interface AppliedTemplateResponse {
  applied: number;
  created: number;
  updated: number;
  touched_document_ids: string[];
}

/**
 * List all document templates for the current tenant.
 */
export async function listDocumentTemplates(includeInactive = false): Promise<DocumentTemplate[]> {
  try {
    // Use regular api instead of docsApi, as templates endpoint is at /api/v1/documents/templates, not /api/v1/db/documents/templates
    const { data } = await api.get<DocumentTemplate[]>("/documents/templates", {
      params: { include_inactive: includeInactive },
    });
    return data || [];
  } catch (e: any) {
    throw new Error(apiErrorMessage(e));
  }
}

/**
 * Get a single document template by ID.
 */
export async function getDocumentTemplate(templateId: string): Promise<DocumentTemplate> {
  try {
    // Use regular api instead of docsApi, as templates endpoint is at /api/v1/documents/templates, not /api/v1/db/documents/templates
    const { data } = await api.get<DocumentTemplate>(`/documents/templates/${templateId}`);
    return data;
  } catch (e: any) {
    throw new Error(apiErrorMessage(e));
  }
}

/**
 * Apply a document template to a candidate.
 */
export async function applyDocumentTemplate(
  candidateId: string,
  payload: ApplyTemplatePayload
): Promise<AppliedTemplateResponse> {
  try {
    const { data } = await docsApi.post<AppliedTemplateResponse>(
      `/candidate/${candidateId}/documents/apply-template`,
      payload
    );
    return data;
  } catch (e: any) {
    throw new Error(apiErrorMessage(e));
  }
}

