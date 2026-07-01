import { docsApi } from "../client";
import type { Document } from "../types";
import { normalizeDocument } from "./normalize";

export async function checkDocument(
  docId: string,
  body: {
    reviewer_id?: string;
    decision: "approved" | "rejected";
    reason_code?: string;
    comment?: string;
    payload?: Record<string, any>;
    meta_json?: Record<string, any>;
  }
): Promise<Document> {
  const payload: Record<string, any> = { ...body };
  if (payload.meta_json && !payload.meta) {
    payload.meta = payload.meta_json;
  }
  const { data } = await docsApi.post(`/documents/${docId}/check`, payload);
  return normalizeDocument(data as any);
}

// Backward-compat
export const postDocumentCheck = checkDocument;

