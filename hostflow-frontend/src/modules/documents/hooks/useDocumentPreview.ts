/**
 * Hook for document preview functionality
 */

import { useCallback, useState, useEffect } from "react";
import type { Document } from "../../../api/types";
import { getDocumentFileUrl, downloadDocumentFile } from "../../../api/documents";
import { formatErrorForDisplay } from "../../../utils/errorHandling";
import { useI18n } from "../../../i18n";
import {
  resolveDocumentUrl,
  guessPreviewable,
  detectPreviewMime,
  filenameFromUrl,
  isProbablyHtmlBlob,
} from "../documentUtils";

interface UseDocumentPreviewProps {
  setError: (error: string | null) => void;
}

export function useDocumentPreview({ setError }: UseDocumentPreviewProps) {
  const { t } = useI18n();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContentType, setPreviewContentType] = useState<string | null>(null);
  const [previewRevoker, setPreviewRevoker] = useState<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      if (previewRevoker) previewRevoker();
    };
  }, [previewRevoker]);

  const openDoc = useCallback(
    async (doc: Document) => {
      setError(null);
      if (previewRevoker) {
        previewRevoker();
        setPreviewRevoker(null);
      }
      setPreviewContentType(null);
      let directLink: string | null = null;
      let directFilename: string | null = null;

      try {
        try {
          const res = await getDocumentFileUrl(doc.id);
          const rawLink = typeof res === "string" ? res : res?.url;
          if (rawLink) {
            const resolved = resolveDocumentUrl(rawLink);
            if (resolved) {
              directLink = resolved;
              directFilename = filenameFromUrl(resolved);
            }
          }
        } catch (fetchLinkError: any) {
          if (fetchLinkError?.response?.status && fetchLinkError.response.status !== 404) {
            throw fetchLinkError;
          }
        }

        const fileData = await downloadDocumentFile(doc.id);
        const { blob, filename, contentType } = fileData;
        const previewable = guessPreviewable(contentType, filename);

        if (!blob || blob.size === 0) {
          if (directLink) {
            window.open(directLink, "_blank", "noopener");
            setPreviewUrl(null);
            setPreviewOpen(false);
            setPreviewContentType(null);
            return;
          }
          setError(t("admin.documents.errors.file_fetch_failed"));
          return;
        }

        const objectUrl = URL.createObjectURL(blob);
        const looksLikeHtml = await isProbablyHtmlBlob(blob, contentType);
        if (looksLikeHtml) {
          URL.revokeObjectURL(objectUrl);
          setPreviewRevoker(null);
          if (directLink) {
            window.open(directLink, "_blank", "noopener");
            return;
          }
          setError(t("admin.documents.errors.file_missing_remote"));
          return;
        }

        if (previewable) {
          if (previewRevoker) previewRevoker();
          const lowerType = (contentType || "").toLowerCase();
          const lowerFilename = (filename || "").toLowerCase();
          const isPdf = lowerType.includes("pdf") || lowerFilename.endsWith(".pdf");
          const previewMime = detectPreviewMime(contentType, filename);
          setPreviewUrl(objectUrl);
          setPreviewOpen(true);
          setPreviewContentType(previewMime ?? (isPdf ? "application/pdf" : "image/*"));
          setPreviewRevoker(() => () => {
            URL.revokeObjectURL(objectUrl);
          });
          return;
        }

        const a = document.createElement("a");
        a.href = objectUrl;
        a.download = filename || doc.title || doc.custom_name || directFilename || "document";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(objectUrl);
        setPreviewRevoker(null);
      } catch (e: any) {
        const message = formatErrorForDisplay(e, {
          fallback: t("admin.documents.errors.file_open_failed"),
        });
        setError(message);
        if (directLink) {
          window.open(directLink, "_blank", "noopener");
        }
      }
    },
    [setError, previewRevoker, t]
  );

  const closePreview = useCallback(() => {
    if (previewRevoker) {
      previewRevoker();
      setPreviewRevoker(null);
    }
    setPreviewOpen(false);
    setPreviewUrl(null);
    setPreviewContentType(null);
  }, [previewRevoker]);

  return {
    previewUrl,
    previewOpen,
    previewContentType,
    openDoc,
    closePreview,
  };
}

