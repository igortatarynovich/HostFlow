/**
 * Hook for document file upload functionality
 */

import { useCallback } from "react";
import type { Document } from "../../../api/types";
import { presignUpload, mockUpload } from "../../../api/documents";
import { formatErrorForDisplay } from "../../../utils/errorHandling";
import { useI18n } from "../../../i18n";
import { MAX_FILE_MB } from "../constants";
import { isTooLarge } from "../documentUtils";

interface UseDocumentUploadProps {
  canManageDocuments: boolean;
  createDocumentFromChecklist: (doc: Document) => Promise<Document>;
  loadAll: () => Promise<void>;
  setError: (error: string | null) => void;
  setReplaceUploading: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  setReplacePct: React.Dispatch<React.SetStateAction<Record<string, number>>>;
  setReplaceFile: React.Dispatch<React.SetStateAction<Record<string, File | null>>>;
  flash: (message: string) => void;
}

export function useDocumentUpload({
  canManageDocuments,
  createDocumentFromChecklist,
  loadAll,
  setError,
  setReplaceUploading,
  setReplacePct,
  setReplaceFile,
  flash,
}: UseDocumentUploadProps) {
  const { t } = useI18n();

  const handleReplaceUpload = useCallback(
    async (doc: Document, file: File) => {
      if (!canManageDocuments) {
        setError(t("admin.documents.errors.permission_upload"));
        return;
      }
      if (isTooLarge(file)) {
        setError(t("admin.documents.errors.file_too_large", { values: { limit: MAX_FILE_MB } }));
        return;
      }

      setReplaceUploading((prev) => ({ ...prev, [doc.id]: true }));
      setReplacePct((prev) => ({ ...prev, [doc.id]: 0 }));

      let timer: number | undefined;
      try {
        let targetDoc = doc;
        const isSynthetic = Boolean((doc.meta_json as any)?.synthetic || (doc.meta as any)?.synthetic);
        if (isSynthetic) {
          targetDoc = await createDocumentFromChecklist(doc);
        }

        timer = window.setInterval(() => {
          setReplacePct((prev) => ({
            ...prev,
            [doc.id]: Math.min(90, (prev[doc.id] || 0) + 5),
          }));
        }, 150) as unknown as number;

        const presign = await presignUpload(targetDoc.id);
        const key = presign?.fields?.key || presign?.key || `documents/${targetDoc.id}/original.bin`;
        await mockUpload({ key, file });

        if (timer) window.clearInterval(timer);
        setReplacePct((prev) => ({ ...prev, [doc.id]: 100 }));
        await loadAll();
        flash(t("admin.documents.notifications.replace_success"));
        setReplaceFile((prev) => ({ ...prev, [doc.id]: null }));
      } catch (e: any) {
        if (timer) window.clearInterval(timer);
        setReplacePct((prev) => ({ ...prev, [doc.id]: 0 }));
        const message = formatErrorForDisplay(e, {
          fallback: t("admin.documents.notifications.replace_failed"),
        });
        setError(message);
      } finally {
        setReplaceUploading((prev) => ({ ...prev, [doc.id]: false }));
        window.setTimeout(() => {
          setReplacePct((prev) => ({ ...prev, [doc.id]: 0 }));
        }, 400);
      }
    },
    [
      canManageDocuments,
      createDocumentFromChecklist,
      loadAll,
      setError,
      setReplaceUploading,
      setReplacePct,
      setReplaceFile,
      flash,
      t,
    ]
  );

  return {
    handleReplaceUpload,
  };
}

