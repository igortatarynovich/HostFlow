import { docsApi } from "../client";
import type { ExtractResult } from "./types";
import { isAxios404 } from "./helpers";

export async function extractDocument(docId: string): Promise<ExtractResult> {
  try {
    const { data } = await docsApi.post<ExtractResult>(`/documents/${docId}/extract`, {});
    return data || { fields: {} };
  } catch (e: any) {
    // если модуль не отдал extract (например, 404) — не рушим UI
    if (isAxios404(e)) return { fields: {} };
    throw e;
  }
}

