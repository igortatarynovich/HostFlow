import { docsApi } from "../client";
import type { DocType } from "./types";

export async function getDocumentTypes(): Promise<DocType[]> {
  const { data } = await docsApi.get<DocType[]>(`/document-types`);
  return data || [];
}

