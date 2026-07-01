/**
 * Hook for document actions (update status, approve, reject, workflow, etc.)
 */

import { useCallback } from "react";
import type { Document, DocumentStatus } from "../../../api/types";
import { patchDocument, checkDocument } from "../../../api/documents";
import { formatErrorForDisplay } from "../../../utils/errorHandling";
import { usePlanLimitModal } from "../../../contexts/PlanLimitModalContext";
import { useI18n } from "../../../i18n";
import { getDocumentFieldsConfig } from "../documentFieldsConfig";
import type { DocumentPatchPayload, CreateCandidateDocumentPayload } from "../../../api/documents";
import { createCandidateDocument } from "../../../api/documents";
import type { CoreFields, MetadataState } from "../types";

interface UseDocumentActionsProps {
  canManageDocuments: boolean;
  candidateId: string;
  updateDocumentState: (doc: Document) => void;
  loadAll: () => Promise<void>;
  setError: (error: string | null) => void;
  setStatusUpdating: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  setCoreSaving: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  flash: (message: string) => void;
  coreEdits: Record<string, CoreFields>;
  metadataEdits: Record<string, MetadataState>;
  getFieldValue: (doc: Document, fieldKey: string, metadataValues: MetadataState) => any;
  coreFromDocument: (doc: Document) => CoreFields;
  onFieldsApplied?: (doc: Document, fields: Record<string, any>) => void;
  onDocumentsChanged?: () => void;
}

export function useDocumentActions({
  canManageDocuments,
  candidateId,
  updateDocumentState,
  loadAll,
  setError,
  setStatusUpdating,
  setCoreSaving,
  flash,
  coreEdits,
  metadataEdits,
  getFieldValue,
  coreFromDocument,
  onFieldsApplied,
  onDocumentsChanged,
}: UseDocumentActionsProps) {
  const { t } = useI18n();
  const planLimitModal = usePlanLimitModal();

  const createDocumentFromChecklist = useCallback(
    async (doc: Document): Promise<Document> => {
      const typeCode = doc.doc_type || doc.type_code || "";
      const payload: CreateCandidateDocumentPayload = {
        owner_id: candidateId,
        doc_type: typeCode,
        status: doc.status || "requested",
        kind: doc.kind || "driver",
        requested_from: doc.requested_from,
        process_type: doc.process_type,
        reminder_days_before: doc.reminder_days_before ?? 30,
      };
      
      // Для additional_document custom_name и user_comment обязательны
      if (typeCode === "additional_document") {
        const title = doc.title ?? doc.custom_name ?? (doc.meta_json as any)?.title;
        if (title) {
          payload.custom_name = String(title).trim();
          payload.title = payload.custom_name;
        } else {
          // Если title отсутствует, используем дефолтное значение
          payload.custom_name = "Additional Document";
          payload.title = payload.custom_name;
        }
        
        // user_comment обязателен для additional_document
        const userComment = doc.user_comment ?? (doc.meta_json as any)?.user_comment ?? (doc.meta_json as any)?.comment;
        if (userComment) {
          payload.user_comment = String(userComment).trim();
        } else {
          // Если user_comment отсутствует, используем дефолтное значение
          payload.user_comment = "Created from checklist";
        }
      }
      
      // Копируем meta_json, удаляя synthetic флаг
      const metaPayload = { ...(doc.meta_json ?? {}) };
      delete (metaPayload as any).synthetic;
      if (Object.keys(metaPayload).length > 0) {
        payload.meta_json = metaPayload;
      }
      
      const created = await createCandidateDocument(payload);
      updateDocumentState(created);
      return created;
    },
    [candidateId, updateDocumentState]
  );

  const updateStatus = useCallback(
    async (doc: Document, newStatus: DocumentStatus) => {
      if (!canManageDocuments) {
        setError(t("admin.documents.errors.permission_edit"));
        return;
      }
      setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
      try {
        let targetDoc = doc;
        const isSynthetic = Boolean((doc.meta_json as any)?.synthetic || (doc.meta as any)?.synthetic);
        if (isSynthetic) {
          targetDoc = await createDocumentFromChecklist(doc);
        }
        const updated = await patchDocument(targetDoc.id, { status: newStatus } as DocumentPatchPayload);
        updateDocumentState(updated);
        flash(t("admin.documents.notifications.status_updated"));
        await loadAll();
        onDocumentsChanged?.();
      } catch (e: any) {
        if (
          planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.status_failed"))
        ) {
          return;
        }
        const message = formatErrorForDisplay(e, {
          fallback: t("admin.documents.notifications.status_failed"),
        });
        setError(message);
      } finally {
        setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
      }
    },
    [
      canManageDocuments,
      createDocumentFromChecklist,
      updateDocumentState,
      loadAll,
      planLimitModal,
      setError,
      setStatusUpdating,
      flash,
      t,
    ]
  );

  const approveDocument = useCallback(
    async (doc: Document) => {
      if (!canManageDocuments) {
        setError(t("admin.documents.errors.permission_approve"));
        return;
      }
      setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
      try {
        let targetDoc = doc;
        const isSynthetic = Boolean((doc.meta_json as any)?.synthetic || (doc.meta as any)?.synthetic);
        if (isSynthetic) {
          targetDoc = await createDocumentFromChecklist(doc);
        }
        const payload: { decision: "approved"; comment?: string } = { decision: "approved" };
        const updated = await checkDocument(targetDoc.id, payload);
        updateDocumentState(updated);
        flash(t("admin.documents.notifications.approve_success"));
        await loadAll();
        onDocumentsChanged?.();
      } catch (e: any) {
        if (
          planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.approve_failed"))
        ) {
          return;
        }
        const message = formatErrorForDisplay(e, {
          fallback: t("admin.documents.notifications.approve_failed"),
        });
        setError(message);
      } finally {
        setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
      }
    },
    [
      canManageDocuments,
      createDocumentFromChecklist,
      updateDocumentState,
      loadAll,
      planLimitModal,
      setError,
      setStatusUpdating,
      flash,
      t,
    ]
  );

  const rejectDocument = useCallback(
    async (doc: Document) => {
      if (!canManageDocuments) {
        setError(t("admin.documents.errors.permission_reject"));
        return;
      }
      const reason = window.prompt(t("admin.documents.prompts.reject_reason"), "") ?? undefined;
      setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
      try {
        let targetDoc = doc;
        const isSynthetic = Boolean((doc.meta_json as any)?.synthetic || (doc.meta as any)?.synthetic);
        if (isSynthetic) {
          targetDoc = await createDocumentFromChecklist(doc);
        }
        const payload: { decision: "rejected"; comment?: string } = { decision: "rejected" };
        if (reason && reason.trim()) payload.comment = reason.trim();
        const updated = await checkDocument(targetDoc.id, payload);
        updateDocumentState(updated);
        flash(t("admin.documents.notifications.reject_success"));
        await loadAll();
        onDocumentsChanged?.();
      } catch (e: any) {
        if (
          planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.reject_failed"))
        ) {
          return;
        }
        const message = formatErrorForDisplay(e, {
          fallback: t("admin.documents.notifications.reject_failed"),
        });
        setError(message);
      } finally {
        setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
      }
    },
    [
      canManageDocuments,
      createDocumentFromChecklist,
      updateDocumentState,
      loadAll,
      planLimitModal,
      setError,
      setStatusUpdating,
      flash,
      t,
    ]
  );

  const startWorkflow = useCallback(
    async (doc: Document) => {
      if (!canManageDocuments) {
        setError(t("admin.documents.errors.permission_workflow"));
        return;
      }
      const workflowSource = doc.workflow ? JSON.parse(JSON.stringify(doc.workflow)) : null;
      if (!workflowSource || !Array.isArray(workflowSource.steps) || !workflowSource.steps.length) {
        return;
      }
      const nowIso = new Date().toISOString();
      const steps = workflowSource.steps.map((step: any) => {
        const status = String(step.status || "").toLowerCase();
        if (status === "done") {
          return { ...step, status: "done" };
        }
        const dueInHours =
          typeof step.due_in_hours === "number" && Number.isFinite(step.due_in_hours) ? step.due_in_hours : null;
        const dueAt =
          step.due_at ??
          (dueInHours != null ? new Date(Date.now() + dueInHours * 60 * 60 * 1000).toISOString() : null);
        return {
          ...step,
          status: "in_progress",
          completed_at: null,
          ordered_at: step.ordered_at ?? nowIso,
          due_at: dueAt,
        };
      });
      workflowSource.steps = steps;
      workflowSource.current_step = steps.find((step: any) => step.status !== "done")?.code ?? null;
      workflowSource.completed = !workflowSource.current_step;

      setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
      try {
        const updated = await patchDocument(doc.id, { workflow: workflowSource } as DocumentPatchPayload);
        updateDocumentState(updated);
        flash(t("admin.documents.notifications.workflow_started"));
        await loadAll();
      } catch (e: any) {
        if (
          planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.workflow_failed"))
        ) {
          return;
        }
        const message = formatErrorForDisplay(e, {
          fallback: t("admin.documents.notifications.workflow_failed"),
        });
        setError(message);
      } finally {
        setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
      }
    },
    [canManageDocuments, updateDocumentState, loadAll, planLimitModal, setError, setStatusUpdating, flash, t]
  );

  const completeWorkflowStep = useCallback(
    async (doc: Document, stepCode: string) => {
      if (!canManageDocuments) {
        setError(t("admin.documents.errors.permission_workflow"));
        return;
      }
      const workflowSource = doc.workflow ? JSON.parse(JSON.stringify(doc.workflow)) : null;
      if (!workflowSource || !Array.isArray(workflowSource.steps) || !workflowSource.steps.length) {
        return;
      }
      const nowIso = new Date().toISOString();
      let nextMarked = false;
      const steps = workflowSource.steps.map((step: any) => {
        const status = String(step.status || "").toLowerCase();
        if (step.code === stepCode) {
          return {
            ...step,
            status: "done",
            completed_at: step.completed_at ?? nowIso,
          };
        }
        if (status === "done") {
          return { ...step, status: "done" };
        }
        if (!nextMarked) {
          nextMarked = true;
          const dueInHours =
            typeof step.due_in_hours === "number" && Number.isFinite(step.due_in_hours) ? step.due_in_hours : null;
          const dueAt =
            step.due_at ??
            (dueInHours != null ? new Date(Date.now() + dueInHours * 60 * 60 * 1000).toISOString() : null);
          return {
            ...step,
            status: "in_progress",
            completed_at: null,
            ordered_at: step.ordered_at ?? nowIso,
            due_at: dueAt,
          };
        }
        return { ...step, status: "pending", completed_at: null };
      });

      workflowSource.steps = steps;
      workflowSource.current_step = steps.find((step: any) => step.status !== "done")?.code ?? null;
      workflowSource.completed = !workflowSource.current_step;

      setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
      try {
        const updated = await patchDocument(doc.id, { workflow: workflowSource } as DocumentPatchPayload);
        updateDocumentState(updated);
        flash(t("admin.documents.notifications.workflow_step_marked"));
        await loadAll();
      } catch (e: any) {
        if (
          planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.workflow_failed"))
        ) {
          return;
        }
        const message = formatErrorForDisplay(e, {
          fallback: t("admin.documents.notifications.workflow_failed"),
        });
        setError(message);
      } finally {
        setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
      }
    },
    [canManageDocuments, updateDocumentState, loadAll, planLimitModal, setError, setStatusUpdating, flash, t]
  );

  const saveCoreFields = useCallback(
    async (doc: Document) => {
      if (!canManageDocuments) {
        setError(t("admin.documents.errors.permission_edit"));
        return;
      }
      setCoreSaving((prev) => ({ ...prev, [doc.id]: true }));
      try {
        let targetDoc = doc;
        const isSynthetic = Boolean((doc.meta_json as any)?.synthetic || (doc.meta as any)?.synthetic);
        if (isSynthetic) {
          targetDoc = await createDocumentFromChecklist(doc);
        }

        const fieldsConfig = getDocumentFieldsConfig(targetDoc.doc_type || targetDoc.type_code || "");
        const edits = coreEdits[targetDoc.id] ?? {};
        const metaEdits = metadataEdits[targetDoc.id] ?? {};
        const payload: DocumentPatchPayload = {};
        const baseMeta: Record<string, any> = { ...(targetDoc.meta_json ?? {}) };
        let metaChanged = false;

        fieldsConfig.forEach((fieldConfig) => {
          const fieldValue = getFieldValue(targetDoc, fieldConfig.key, metaEdits);

          if (fieldConfig.key === "number") {
            const value = edits.number !== undefined ? edits.number : fieldValue;
            if (value !== undefined) {
              payload.number = value && String(value).trim() ? String(value).trim() : null;
            }
          } else if (fieldConfig.key === "issue_date") {
            const value = edits.issue_date !== undefined ? edits.issue_date : fieldValue;
            if (value !== undefined) {
              payload.issue_date = value ? String(value).slice(0, 10) : null;
            }
          } else if (fieldConfig.key === "expire_date") {
            const value = edits.expire_date !== undefined ? edits.expire_date : fieldValue;
            if (value !== undefined) {
              payload.expire_date = value ? String(value).slice(0, 10) : null;
            }
          } else if (fieldConfig.key === "valid_from") {
            const value = edits.valid_from !== undefined ? edits.valid_from : fieldValue;
            if (value !== undefined) {
              payload.valid_from = value ? String(value).slice(0, 10) : null;
            }
          } else if (fieldConfig.key === "ordered_at") {
            const value = edits.ordered_at !== undefined ? edits.ordered_at : fieldValue;
            if (value !== undefined) {
              payload.ordered_at = value ? String(value).slice(0, 10) : null;
            }
          } else {
            const value = metaEdits[fieldConfig.key] !== undefined ? metaEdits[fieldConfig.key] : fieldValue;
            if (value !== undefined) {
              const isEmpty =
                value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0);
              if (isEmpty) {
                if (baseMeta[fieldConfig.key] !== undefined) {
                  delete baseMeta[fieldConfig.key];
                  metaChanged = true;
                }
              } else {
                baseMeta[fieldConfig.key] = value;
                metaChanged = true;
              }
            }
          }
        });

        if (metaChanged) {
          payload.meta_json = baseMeta;
        }

        if (Object.keys(payload).length === 0) {
          return;
        }

        const updated = await patchDocument(targetDoc.id, payload);
        updateDocumentState(updated);
        if (onFieldsApplied) {
          onFieldsApplied(updated, payload.meta_json ?? {});
        }
        flash(t("admin.documents.notifications.core_saved"));
        await loadAll();
      } catch (e: any) {
        if (
          planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.core_failed"))
        ) {
          return;
        }
        const message = formatErrorForDisplay(e, {
          fallback: t("admin.documents.notifications.core_failed"),
        });
        setError(message);
      } finally {
        setCoreSaving((prev) => ({ ...prev, [doc.id]: false }));
      }
    },
    [
      canManageDocuments,
      createDocumentFromChecklist,
      coreEdits,
      metadataEdits,
      getFieldValue,
      updateDocumentState,
      loadAll,
      planLimitModal,
      setError,
      setCoreSaving,
      flash,
      onFieldsApplied,
      t,
    ]
  );

  const deleteDocumentFile = useCallback(
    async (doc: Document) => {
      if (!canManageDocuments) {
        setError(t("admin.documents.errors.permission_delete"));
        return;
      }
      const docHasFiles = doc.has_files ?? (Array.isArray(doc.files) && doc.files.length > 0);
      if (!docHasFiles) {
        setError(t("admin.documents.errors.no_file_to_delete", { defaultValue: "No file to delete" }));
        return;
      }
      if (!window.confirm(t("admin.documents.prompts.delete_file_confirm", { defaultValue: "Are you sure you want to delete this file?" }))) {
        return;
      }
      setStatusUpdating((prev) => ({ ...prev, [doc.id]: true }));
      try {
        let targetDoc = doc;
        const isSynthetic = Boolean((doc.meta_json as any)?.synthetic || (doc.meta as any)?.synthetic);
        if (isSynthetic) {
          targetDoc = await createDocumentFromChecklist(doc);
        }
        const updated = await patchDocument(targetDoc.id, { files: [] } as DocumentPatchPayload);
        const updatedWithNoFiles: Document = {
          ...updated,
          has_files: false,
          files: [],
        };
        updateDocumentState(updatedWithNoFiles);
        flash(t("admin.documents.notifications.file_deleted", { defaultValue: "File deleted" }));
      } catch (e: any) {
        if (
          planLimitModal?.showPlanLimitIfNeeded(e, t("admin.documents.notifications.delete_failed"))
        ) {
          return;
        }
        const message = formatErrorForDisplay(e, {
          fallback: t("admin.documents.notifications.delete_failed"),
        });
        setError(message);
      } finally {
        setStatusUpdating((prev) => ({ ...prev, [doc.id]: false }));
      }
    },
    [
      canManageDocuments,
      createDocumentFromChecklist,
      updateDocumentState,
      planLimitModal,
      setError,
      setStatusUpdating,
      flash,
      t,
    ]
  );

  return {
    updateStatus,
    approveDocument,
    rejectDocument,
    startWorkflow,
    completeWorkflowStep,
    saveCoreFields,
    deleteDocumentFile,
    createDocumentFromChecklist,
  };
}

