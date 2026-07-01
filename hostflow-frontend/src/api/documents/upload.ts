import { docsApi } from "../client";
import type { PresignUpload } from "./types";

export async function presignUpload(docId: string): Promise<PresignUpload> {
  const { data } = await docsApi.post<PresignUpload>(`/documents/${docId}/presign-upload`, {});
  return data;
}

// Фактическая загрузка к presigned url (для реального S3/GCS). В dev используем mockUpload.
export async function uploadViaPresign(presign: PresignUpload, file: File): Promise<Response> {
  if (presign.method === "POST") {
    const fd = new FormData();
    if (presign.fields) {
      for (const [k, v] of Object.entries(presign.fields)) {
        fd.append(k, v);
      }
    }
    fd.append("file", file);
    const resp = await fetch(presign.url!, { method: "POST", body: fd });
    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      throw new Error(`Presign POST failed: ${resp.status} ${text}`);
    }
    return resp;
  } else {
    const resp = await fetch(presign.url!, {
      method: "PUT",
      body: file,
      headers: { "Content-Type": file.type || "application/octet-stream" },
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      throw new Error(`Presign PUT failed: ${resp.status} ${text}`);
    }
    return resp;
  }
}

// ---- Local dev helper (mock upload to local storage) ----
export async function mockUpload(params: {
  key: string;
  file: File | Blob;
}): Promise<{ ok: boolean; stored_as: string }> {
  const fd = new FormData();
  fd.append("key", params.key);
  fd.append("file", params.file);
  const { data } = await docsApi.post<{ ok: boolean; stored_as: string; url?: string; version?: number }>(
    "/mock-upload",
    fd,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

