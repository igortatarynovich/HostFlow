/**
 * Component for displaying a single document card with accordion functionality
 */

import { memo, useState } from "react";
import clsx from "clsx";
import type { Document, DocumentStatus } from "../../../api/types";
import { DocumentFieldInput } from "./DocumentFieldInput";
import { getDocumentFieldsConfig } from "../documentFieldsConfig";
import {
  DOCUMENT_STATUS_META,
  READY_STATUSES,
  NEGATIVE_STATUSES,
  EXPIRING_SOON_THRESHOLD_DAYS,
} from "../constants";
import { formatDate, primaryStatus, resolveRequestedFromDate, isExpiringSoonDoc, normalizeDocTypeCode, resolveDocTypeLabel } from "../documentUtils";
import { buildMetadataStateFromDoc } from "../documentUtils";
import type { DocType, MetadataState, CoreFields } from "../types";
import { useI18n } from "../../../i18n";
import { MAX_FILE_MB } from "../constants";
import { isTooLarge } from "../documentUtils";

interface DocumentCardProps {
  doc: Document;
  typeByCode: Map<string, DocType>;
  metadataFieldMap: Map<string, any[]>;
  coreEdits: Record<string, CoreFields>;
  metadataEdits: Record<string, MetadataState>;
  statusUpdating: Record<string, boolean>;
  coreSaving: Record<string, boolean>;
  replaceFile: Record<string, File | null>;
  replacePct: Record<string, number>;
  replaceUploading: Record<string, boolean>;
  expandedDocs: Record<string, boolean>;
  canManageDocuments: boolean;
  coreFromDocument: (doc: Document) => CoreFields;
  translateStatus: (status: DocumentStatus | string) => string;
  getFieldValue: (doc: Document, fieldKey: string, metadataValues: MetadataState) => any;
  updateFieldValue: (doc: Document, fieldKey: string, value: any) => void;
  updateStatus: (doc: Document, newStatus: DocumentStatus) => void;
  approveDocument: (doc: Document) => void;
  rejectDocument: (doc: Document) => void;
  saveCoreFields: (doc: Document) => void;
  deleteDocumentFile: (doc: Document) => void;
  deleteDocument?: (docId: string) => void;
  openDoc: (doc: Document) => void;
  handleReplaceUpload: (doc: Document, file: File) => Promise<void>;
  setReplaceFile: React.Dispatch<React.SetStateAction<Record<string, File | null>>>;
  setExpandedDocs: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  setError: (error: string | null) => void;
}

export const DocumentCard = memo(function DocumentCard({
  doc,
  typeByCode,
  metadataFieldMap,
  coreEdits,
  metadataEdits,
  statusUpdating,
  coreSaving,
  replaceFile,
  replacePct,
  replaceUploading,
  expandedDocs,
  canManageDocuments,
  coreFromDocument,
  translateStatus,
  getFieldValue,
  updateFieldValue,
  updateStatus,
  approveDocument,
  rejectDocument,
  saveCoreFields,
  deleteDocumentFile,
  deleteDocument,
  openDoc,
  handleReplaceUpload,
  setReplaceFile,
  setExpandedDocs,
  setError,
}: DocumentCardProps) {
  const { t } = useI18n();

  const normalizedTypeCode = normalizeDocTypeCode(doc.type_code || doc.doc_type || "");
  const typeInfo = typeByCode.get(normalizedTypeCode) ?? typeByCode.get(doc.doc_type) ?? typeByCode.get(doc.type_code);
  const typeLabel = resolveDocTypeLabel(t, normalizedTypeCode || doc.doc_type || doc.type_code || "", typeInfo?.name);
  const title = doc.custom_name || doc.title || typeLabel;
  const statusValue = primaryStatus(doc);
  const statusMeta =
    DOCUMENT_STATUS_META[statusValue] ?? {
      labelKey: statusValue,
      color: "bg-slate-100 text-slate-600",
      order: 99,
    };
  const metadataFields = metadataFieldMap.get(normalizedTypeCode || doc.doc_type) ?? [];
  const metadataValues = metadataEdits[doc.id] ?? buildMetadataStateFromDoc(doc, metadataFields);
  const statusLabel = translateStatus(statusValue);
  const selectStatus = statusValue;
  const hasFiles = doc.has_files ?? (Array.isArray(doc.files) && doc.files.length > 0);
  const isExpiringSoon = isExpiringSoonDoc(doc);
  const fieldsConfig = getDocumentFieldsConfig(normalizedTypeCode || doc.doc_type || doc.type_code || "");

  const expanded = Boolean(expandedDocs[doc.id]);
  const toggleExpanded = () => {
    setExpandedDocs((prev) => ({ ...prev, [doc.id]: !prev[doc.id] }));
  };

  const selectedReplaceFile = replaceFile[doc.id] ?? null;
  const uploadProgress = replacePct[doc.id] || 0;
  const isReplacing = Boolean(replaceUploading[doc.id]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = e.currentTarget.files?.[0] ?? null;
    e.currentTarget.value = "";
    if (!next) return;
    if (isTooLarge(next)) {
      setError(t("admin.documents.errors.file_too_large", { values: { limit: MAX_FILE_MB } }));
      return;
    }
    setError(null);
    setReplaceFile((prev) => ({ ...prev, [doc.id]: next }));
  };

  const handleReplaceUploadClick = async () => {
    const nextFile = replaceFile[doc.id];
    if (!nextFile) return;
    await handleReplaceUpload(doc, nextFile);
  };

  return (
    <div key={doc.id} className="rounded border border-slate-200 bg-white shadow-sm">
      <div
        className="flex flex-col gap-3 p-4 hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between"
        onClick={toggleExpanded}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <span className="text-sm">{expanded ? "▾" : "▸"}</span>
          <div className="flex-1 min-w-0">
            <div className="text-base font-semibold text-slate-800">{title}</div>
            {!expanded && (
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500 mt-1">
                <span>{typeLabel}</span>
                {doc.number && <span>{t("admin.documents.labels.number")} {doc.number}</span>}
                {doc.issue_date && (
                  <span>
                    {t("admin.documents.labels.issue_date")} {formatDate(doc.issue_date)}
                  </span>
                )}
                {doc.expire_date && (
                  <span>
                    {t("admin.documents.labels.expire_date")} {formatDate(doc.expire_date)}
                  </span>
                )}
                {doc.ordered_at && (
                  <span>
                    {t("admin.documents.labels.ordered_at", { defaultValue: "Ordered" })} {formatDate(doc.ordered_at)}
                  </span>
                )}
                <span
                  className={clsx(
                    "inline-flex items-center gap-1 rounded-full px-2 py-0.5",
                    hasFiles ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"
                  )}
                >
                  {hasFiles ? t("admin.documents.badges.files_present") : t("admin.documents.badges.files_missing")}
                </span>
                {isExpiringSoon && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-amber-700">
                    {t("admin.documents.badges.expiring", { values: { days: EXPIRING_SOON_THRESHOLD_DAYS } })}
                  </span>
                )}
              </div>
            )}
          </div>
          <span
            className={clsx(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs",
              statusMeta.color
            )}
          >
            {statusLabel}
            {statusUpdating[doc.id] && <span className="text-[10px] text-slate-600">…</span>}
          </span>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end" onClick={(e) => e.stopPropagation()}>
          <label className="flex w-full items-center gap-2 text-xs sm:w-auto">
            <span className="text-slate-600">{t("admin.documents.table.status")}</span>
            <select
              className="input input-sm w-full sm:w-auto"
              value={selectStatus}
              onChange={(e) => updateStatus(doc, e.target.value as DocumentStatus)}
              disabled={!canManageDocuments || statusUpdating[doc.id]}
            >
              {Object.keys(DOCUMENT_STATUS_META).map((status) => (
                <option key={status} value={status}>
                  {translateStatus(status)}
                </option>
              ))}
            </select>
          </label>
          <button
            className="btn-primary btn-xs w-full sm:w-auto"
            onClick={() => approveDocument(doc)}
            disabled={!canManageDocuments || statusUpdating[doc.id] || selectStatus === "approved"}
          >
            {t("admin.documents.actions.approve")}
          </button>
          <button
            className="btn-danger btn-xs w-full sm:w-auto"
            onClick={() => rejectDocument(doc)}
            disabled={!canManageDocuments || statusUpdating[doc.id]}
          >
            {t("admin.documents.actions.reject")}
          </button>
          <label className="input btn-xs flex w-full cursor-pointer items-center gap-2 sm:w-auto">
            <span className="text-xs">{t("admin.documents.actions.choose_file")}</span>
            <input type="file" className="hidden" onChange={handleFileSelect} />
          </label>
          {selectedReplaceFile && (
            <button
              className="btn-primary btn-xs w-full sm:w-auto"
              onClick={handleReplaceUploadClick}
              disabled={isReplacing}
            >
              {isReplacing
                ? t("admin.documents.status.uploading_with_progress", { values: { percent: uploadProgress } })
                : t("admin.documents.actions.upload_file")}
            </button>
          )}
          {hasFiles && (
            <button type="button" className="btn-secondary btn-xs w-full sm:w-auto" onClick={() => openDoc(doc)}>
              {t("admin.documents.actions.open")}
            </button>
          )}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-slate-100 p-4 space-y-4">
          <div className="space-y-2 rounded border border-slate-100 bg-slate-50 p-3">
            <div className="grid gap-2 md:grid-cols-3">
              {fieldsConfig.map((fieldConfig) => {
                const fieldValue = getFieldValue(doc, fieldConfig.key, metadataValues);
                return (
                  <DocumentFieldInput
                    key={fieldConfig.key}
                    fieldConfig={fieldConfig}
                    value={fieldValue}
                    onChange={(value) => updateFieldValue(doc, fieldConfig.key, value)}
                    disabled={!canManageDocuments}
                  />
                );
              })}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="btn-primary btn-xs"
              onClick={() => saveCoreFields(doc)}
              disabled={!canManageDocuments || coreSaving[doc.id]}
            >
              {coreSaving[doc.id] ? t("admin.documents.status.saving") : t("common.actions.save")}
            </button>
            {hasFiles && (
              <button
                className="btn-danger btn-xs"
                onClick={() => deleteDocumentFile(doc)}
                disabled={!canManageDocuments || statusUpdating[doc.id] || coreSaving[doc.id]}
              >
                {t("admin.documents.actions.delete_file", { defaultValue: "Удалить файл" })}
              </button>
            )}
            {deleteDocument && !doc.id.startsWith("synthetic::") && (
              <button
                className="btn-danger btn-xs"
                onClick={() => {
                  if (confirm(t("admin.documents.actions.confirm_delete_document", { defaultValue: "Вы уверены, что хотите удалить этот документ?" }))) {
                    deleteDocument(doc.id);
                  }
                }}
                disabled={!canManageDocuments || statusUpdating[doc.id] || coreSaving[doc.id]}
              >
                {t("admin.documents.actions.delete_document", { defaultValue: "Удалить документ" })}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
});
