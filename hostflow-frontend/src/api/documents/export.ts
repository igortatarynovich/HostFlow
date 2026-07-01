import { docsApi } from "../client";

export async function exportDocumentsJSON(ownerId: string) {
  const { data } = await docsApi.get<any>(`/candidate/${ownerId}/documents/export.json`);
  return data;
}

export async function exportDocumentsCSV(ownerId: string): Promise<Blob> {
  const { data } = await docsApi.get<Blob>(`/candidate/${ownerId}/documents/export.csv`, {
    responseType: "blob",
  });
  return data;
}

export async function exportCandidateBundle(ownerId: string): Promise<Blob> {
  const { data } = await docsApi.get<Blob>(`/candidate/${ownerId}/export.zip`, {
    responseType: "blob",
  });
  return data;
}

