import { docsApi } from "../client";
import type { DocumentFileDownload } from "./types";

const parseContentDisposition = (value: string | null | undefined): string | null => {
  if (!value) return null;
  const match = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(value);
  if (!match || !match[1]) return null;
  try {
    return decodeURIComponent(match[1].replace(/["']/g, ""));
  } catch {
    return match[1].replace(/["']/g, "");
  }
};

export async function downloadDocumentFile(
  docId: string,
  options?: { viewerChannel?: string },
): Promise<DocumentFileDownload> {
  const requestHeaders: Record<string, string> = {}
  if (options?.viewerChannel) {
    requestHeaders['X-Document-Viewer-Channel'] = options.viewerChannel
  }
  const response = await docsApi.get<Blob>(`/documents/${docId}/file`, {
    responseType: 'blob',
    headers: Object.keys(requestHeaders).length ? requestHeaders : undefined,
  });
  const headers = response.headers as any;
  const getHeader = (name: string): string | undefined => {
    if (!headers) return undefined;
    if (typeof headers.get === "function") {
      const direct = headers.get(name);
      if (direct) return direct;
    }
    return headers[name] ?? headers[name.toLowerCase()] ?? headers[name.toUpperCase()];
  };
  const disposition = getHeader("content-disposition");
  const contentType = getHeader("content-type");
  return {
    blob: response.data,
    filename: parseContentDisposition(disposition),
    contentType: typeof contentType === "string" ? contentType : null,
  };
}

export async function getDocumentFileUrl(
  docId: string,
  options?: { viewerChannel?: string },
): Promise<{ url: string; expires_at?: string }> {
  const requestHeaders: Record<string, string> = {}
  if (options?.viewerChannel) {
    requestHeaders['X-Document-Viewer-Channel'] = options.viewerChannel
  }
  const { data } = await docsApi.get<{ url: string; expires_at?: string }>(
    `/documents/${docId}/file-url`,
    { headers: Object.keys(requestHeaders).length ? requestHeaders : undefined },
  );
  return data;
}

