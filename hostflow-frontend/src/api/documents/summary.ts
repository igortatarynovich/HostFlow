import { docsApi } from "../client";
import type { CandidateDocumentChecklist, CandidateDocumentsSummaryResponse } from "../types";
import { q, isPlainObject } from "./helpers";
import { normalizeSummaryResponse, normalizeChecklist } from "./normalize";

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

