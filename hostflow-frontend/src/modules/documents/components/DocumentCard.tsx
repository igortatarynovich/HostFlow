/**
 * Component for displaying a single document card with accordion functionality
 */

import { memo, useRef, useState } from "react";
import clsx from "clsx";
import type { Document, DocumentStatus } from "../../../api/types";
import { DocumentFieldInput } from "./DocumentFieldInput";
import { getDocumentFieldsConfig } from "../documentFieldsConfig";
import {
  DOCUMENT_STATUS_META,
} from "../constants";
import { formatDate, primaryStatus, resolveRequestedFromDate, normalizeDocTypeCode, resolveDocTypeLabel, documentHasFiles, statusRequiresUploadedFile } from "../documentUtils";
import { runtimeBadgeFromDocument } from "../../../utils/runtimeBadgePresentation";
import { buildMetadataStateFromDoc } from "../documentUtils";
import type { DocType, MetadataState, CoreFields } from "../types";
import { useI18n } from "../../../i18n";
import { MAX_FILE_MB } from "../constants";
import { isTooLarge } from "../documentUtils";
import { NextActionBadge } from "../../../components/candidate/NextActionBadge";
import { useDocumentNextAction } from "../../../components/document/useDocumentNextAction";
import { DocumentReminders } from "./DocumentReminders";
import { DocumentLastCheck } from "./DocumentLastCheck";

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
  variant?: "full" | "compact";
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
  variant = "full",
}: DocumentCardProps) {
  const { t } = useI18n();
  const isCompact = variant === "compact";

  const normalizedTypeCode = normalizeDocTypeCode(doc.type_code || doc.doc_type || "");
  const typeInfo = typeByCode.get(normalizedTypeCode) ?? typeByCode.get(doc.doc_type) ?? typeByCode.get(doc.type_code);
  const typeLabel = resolveDocTypeLabel(t, normalizedTypeCode || doc.doc_type || doc.type_code || "", typeInfo?.name);
  const title = doc.custom_name || doc.title || typeLabel;
  const statusValue = primaryStatus(doc);
  const badgePresentation = runtimeBadgeFromDocument(doc);
  const statusMeta = {
    labelKey: badgePresentation.labelKey,
    color: badgePresentation.className,
    order: DOCUMENT_STATUS_META[statusValue]?.order ?? 99,
  };
  const metadataFields = metadataFieldMap.get(normalizedTypeCode || doc.doc_type) ?? [];
  const metadataValues = metadataEdits[doc.id] ?? buildMetadataStateFromDoc(doc, metadataFields);
  const statusLabel = t(badgePresentation.labelKey, { defaultValue: badgePresentation.badge });
  const selectStatus = statusValue;
  const hasFiles = documentHasFiles(doc);
  const firstFileName = Array.isArray(doc.files) ? doc.files[0]?.name : undefined;
  const needsVerification = hasFiles && badgePresentation.badge === "pending";
  const isApproved = hasFiles && (badgePresentation.badge === "approved" || selectStatus === "approved");
  const canApprove = canManageDocuments && hasFiles;
  const showTypeLabel = Boolean(typeLabel) && typeLabel.trim().toLowerCase() !== String(title || "").trim().toLowerCase();
  const showStatusChip = isCompact || hasFiles;
  const showNextAction = !isCompact && hasFiles && badgePresentation.badge !== "missing";
  const fieldsConfig = getDocumentFieldsConfig(normalizedTypeCode || doc.doc_type || doc.type_code || "");
  const docReminders = Array.isArray(doc.reminders) ? doc.reminders : [];
  const hasLastCheck = Boolean(doc.last_check);
  const showFollowUps = docReminders.length > 0 || hasLastCheck;
  const expanded = !isCompact && Boolean(expandedDocs[doc.id]);
  const showMetaRow =
    !expanded &&
    Boolean(
      showTypeLabel ||
        doc.number ||
        doc.issue_date ||
        doc.expire_date ||
        doc.expires_at ||
        doc.ordered_at ||
        hasFiles,
    );

  /** Next-action badge: hidden in `compact` (no room); fingerprint reflects status/files/expiry. */
  const docNextActionFingerprint = `${doc.status ?? ''}|${doc.expire_date ?? doc.expires_at ?? ''}|${(doc as { deleted_at?: string | null }).deleted_at ?? ''}|${hasFiles ? 1 : 0}`;
  const { data: docNextAction, loading: docNextActionLoading, error: docNextActionError } =
    useDocumentNextAction(showNextAction ? doc.id : null, docNextActionFingerprint);

  const toggleExpanded = () => {
    if (isCompact) return;
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

  const replaceInputRef = useRef<HTMLInputElement | null>(null);
  const triggerReplace = () => {
    if (!replaceInputRef.current) return;
    replaceInputRef.current.click();
  };

  const handleReplaceSelectedFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const nextFile = e.currentTarget.files?.[0] ?? null;
    e.currentTarget.value = "";
    if (!nextFile) return;

    if (isTooLarge(nextFile)) {
      setError(t("admin.documents.errors.file_too_large", { values: { limit: MAX_FILE_MB } }));
      return;
    }
    setError(null);
    // Immediately upload for side-panel UX.
    setReplaceFile((prev) => ({ ...prev, [doc.id]: nextFile }));
    await handleReplaceUpload(doc, nextFile);
  };

  return (
    <div key={doc.id} className="rounded border border-slate-200 bg-white shadow-sm">
      <div
        className="flex flex-col gap-3 p-4 hover:bg-slate-50 xl:flex-row xl:items-start xl:justify-between"
        onClick={toggleExpanded}
      >
        <div className="flex min-w-0 flex-1 items-start gap-3">
          {!isCompact && <span className="mt-0.5 shrink-0 text-sm">{expanded ? "▾" : "▸"}</span>}
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <div className="text-base font-semibold text-slate-800 break-words">{title}</div>
              {showStatusChip ? (
              <span
                className={clsx(
                  "inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs",
                  statusMeta.color
                )}
              >
                {statusLabel}
                {badgePresentation.showSatisfactionIndicator ? (
                  <span className="text-[10px] opacity-80" title={t("admin.documents.runtime_badges.satisfies_requirement", { defaultValue: "Satisfies requirement" })}>
                    ✓
                  </span>
                ) : null}
                {statusUpdating[doc.id] && <span className="text-[10px] text-slate-600">…</span>}
              </span>
              ) : null}
              {showNextAction ? (
                <NextActionBadge
                  dto={docNextAction}
                  loading={docNextActionLoading}
                  error={docNextActionError}
                />
              ) : null}
            </div>
            {showMetaRow ? (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                {showTypeLabel ? <span>{typeLabel}</span> : null}
                {doc.number && <span>{t("admin.documents.labels.number")} {doc.number}</span>}
                {doc.issue_date && (
                  <span>
                    {t("admin.documents.labels.issue_date")} {formatDate(doc.issue_date)}
                  </span>
                )}
                {(doc.expire_date || doc.expires_at) && (
                  <span>
                    {t("admin.documents.labels.expire_date")} {formatDate(doc.expire_date || doc.expires_at)}
                  </span>
                )}
                {doc.ordered_at && (
                  <span>
                    {t("admin.documents.labels.ordered_at", { defaultValue: "Ordered" })} {formatDate(doc.ordered_at)}
                  </span>
                )}
                {hasFiles ? (
                  <>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                      {t("admin.documents.badges.files_present")}
                    </span>
                    {firstFileName ? <span className="text-xs text-slate-600">{firstFileName}</span> : null}
                  </>
                ) : null}
              </div>
            ) : null}
            {showFollowUps ? (
              <div
                className="mt-1.5 flex flex-col gap-1"
                onClick={(e) => {
                  if (!isCompact) e.stopPropagation();
                }}
              >
                {docReminders.length > 0 ? <DocumentReminders reminders={docReminders} /> : null}
                {hasLastCheck ? <DocumentLastCheck check={doc.last_check} variant="inline" /> : null}
              </div>
            ) : null}
          </div>
        </div>
        <div
          className="flex w-full shrink-0 flex-wrap items-center gap-2 xl:w-auto xl:max-w-[46%] xl:justify-end"
          onClick={(e) => e.stopPropagation()}
        >
          {isCompact ? (
            <>
              {needsVerification ? (
                <div className="w-full rounded-md border border-amber-300 bg-amber-50 px-2.5 py-2 text-[11px] font-medium leading-snug text-amber-950">
                  {t("admin.documents.hints.review_required")}
                </div>
              ) : null}
              <input ref={replaceInputRef} type="file" className="hidden" onChange={handleReplaceSelectedFile} />
              <button
                type="button"
                className="btn-primary btn-xs w-full sm:w-auto"
                onClick={triggerReplace}
                disabled={!canManageDocuments || statusUpdating[doc.id] || replaceUploading[doc.id]}
              >
                {replaceUploading[doc.id]
                  ? t("admin.documents.status.uploading", { defaultValue: "Uploading..." })
                  : hasFiles
                    ? t("admin.documents.actions.replace")
                    : t("admin.documents.actions.choose_file")}
              </button>
              {hasFiles ? (
                <button
                  type="button"
                  className="btn-danger btn-xs w-full sm:w-auto"
                  onClick={() => deleteDocumentFile(doc)}
                  disabled={!canManageDocuments || statusUpdating[doc.id] || coreSaving[doc.id]}
                >
                  {t("admin.documents.actions.delete_file")}
                </button>
              ) : null}
            </>
          ) : (
            <>
              {needsVerification && !isApproved ? (
                <div className="w-full rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-medium leading-snug text-amber-950 sm:max-w-xl">
                  {t("admin.documents.hints.review_required")}
                </div>
              ) : null}
              {!isApproved ? (
                <>
              <label className="flex w-full items-center gap-2 text-xs sm:w-auto">
                <span className="text-slate-600">{t("admin.documents.table.status")}</span>
                <select
                  className="input input-sm w-full sm:w-auto"
                  value={selectStatus}
                  onChange={(e) => updateStatus(doc, e.target.value as DocumentStatus)}
                  disabled={!canManageDocuments || statusUpdating[doc.id]}
                >
                  {Object.keys(DOCUMENT_STATUS_META).map((status) => (
                    <option
                      key={status}
                      value={status}
                      disabled={!hasFiles && statusRequiresUploadedFile(status)}
                    >
                      {translateStatus(status)}
                    </option>
                  ))}
                </select>
              </label>
              {hasFiles ? (
                <>
              <button
                className={clsx("btn-xs w-full sm:w-auto", needsVerification ? "btn-primary ring-2 ring-emerald-200" : "btn-primary")}
                onClick={() => approveDocument(doc)}
                disabled={!canApprove || statusUpdating[doc.id]}
              >
                {t("admin.documents.actions.approve")}
              </button>
              <button
                className={clsx("btn-xs w-full sm:w-auto", needsVerification ? "btn-danger ring-2 ring-rose-200" : "btn-danger")}
                onClick={() => rejectDocument(doc)}
                disabled={!canManageDocuments || statusUpdating[doc.id]}
              >
                {t("admin.documents.actions.reject")}
              </button>
                </>
              ) : null}
                </>
              ) : null}
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
                    ? t("admin.documents.status.uploading_with_progress", { values: { progress: uploadProgress } })
                    : t("admin.documents.actions.upload_file")}
                </button>
              )}
              {hasFiles && (
                <button type="button" className="btn-secondary btn-xs w-full sm:w-auto" onClick={() => openDoc(doc)}>
                  {t("admin.documents.actions.open")}
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {expanded && (
        <div className="space-y-3 border-t border-slate-100 p-4">
          <div className="grid gap-2 rounded bg-slate-50/90 p-3 md:grid-cols-3">
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
