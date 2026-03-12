import { docsApi } from "../client";
import type { Document, DocumentCheck } from "../types";
import type { ListDocumentsOptions } from "./types";
import { q, isAxios404 } from "./helpers";
import { normalizeDocument, normalizeCheck } from "./normalize";

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

export async function getDocument(
  docId: string,
  opts?: { includeChecks?: boolean }
): Promise<Document & { checks?: DocumentCheck[] }> {
  const { includeChecks } = opts || {};
  const { data } = await docsApi.get<any>(`/documents/${docId}`, q({ include_checks: includeChecks }));
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

