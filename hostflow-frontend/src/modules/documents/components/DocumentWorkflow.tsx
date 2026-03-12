/**
 * Component for displaying document workflow steps
 */

import { memo } from "react";
import clsx from "clsx";
import type { Document, DocumentWorkflow, DocumentWorkflowStep, DocumentStatus } from "../../../api/types";
import { DOCUMENT_STATUS_META } from "../constants";
import { formatDateTime } from "../documentUtils";
import { useI18n } from "../../../i18n";

interface DocumentWorkflowProps {
  doc: Document;
  workflow: DocumentWorkflow | undefined;
  translateStatus: (status: DocumentStatus | string) => string;
  translateProcess: (value: string | null | undefined) => string | null;
  canManageDocuments: boolean;
  canModify: boolean;
  onStartWorkflow: (doc: Document) => void;
  onCompleteStep: (doc: Document, stepCode: string) => void;
}

export const DocumentWorkflow = memo(function DocumentWorkflow({
  doc,
  workflow,
  translateStatus,
  translateProcess,
  canManageDocuments,
  canModify,
  onStartWorkflow,
  onCompleteStep,
}: DocumentWorkflowProps) {
  const { t } = useI18n();
  const steps = Array.isArray(workflow?.steps) ? workflow!.steps : [];
  if (!steps.length) return null;

  const completed = steps.filter((step) => String(step.status).toLowerCase() === "done").length;
  const total = steps.length;
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;
  const processLabel = translateProcess(workflow?.process_type ?? doc.process_type) ?? doc.process_type;
  const hasActive = steps.some((step) => String(step.status || "").toLowerCase() === "in_progress");
  const unfinishedExists = steps.some((step) => String(step.status || "").toLowerCase() !== "done");
  const canStart = canModify && !hasActive && unfinishedExists;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
        <span className="font-semibold text-slate-700">{t("admin.documents.workflow.title")}</span>
        <span>{processLabel}</span>
        <span className="ml-auto text-slate-500">{completed}/{total}</span>
        {canStart && (
          <button className="btn-primary btn-xs" onClick={() => onStartWorkflow(doc)}>
            {t("admin.documents.actions.order")}
          </button>
        )}
      </div>
      <div className="h-1.5 rounded bg-slate-200">
        <div className="h-full rounded bg-blue-500" style={{ width: `${progress}%` }} />
      </div>
      <div className="space-y-1">
        {steps.map((step: DocumentWorkflowStep) => {
          const rawStatus = String(step.status || "pending").toLowerCase();
          const isDone = rawStatus === "done";
          const badge = DOCUMENT_STATUS_META[step.status as DocumentStatus]?.color ?? "bg-slate-100 text-slate-600";
          const dueAtDate = step.due_at ? new Date(step.due_at) : null;
          const overdue = Boolean(dueAtDate && dueAtDate.getTime() < Date.now() && !isDone);
          return (
            <div key={step.code} className="rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-slate-700">{step.title || step.code}</span>
                <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5", badge)}>
                  {translateStatus(step.status || rawStatus)}
                </span>
                {step.ordered_at && (
                  <span className="text-slate-500">
                    {t("admin.documents.workflow.ordered_at", {
                      values: { datetime: formatDateTime(step.ordered_at) ?? "" },
                    })}
                  </span>
                )}
                {step.due_at && (
                  <span className={clsx("text-slate-500", overdue && "text-rose-600 font-semibold")}>
                    {t("admin.documents.workflow.due_at", {
                      values: { datetime: formatDateTime(step.due_at) ?? "" },
                    })}
                  </span>
                )}
                {typeof step.due_in_hours === "number" && !Number.isNaN(step.due_in_hours) && (
                  <span className="text-slate-400">
                    {t("admin.documents.workflow.due_in_hours", { values: { hours: step.due_in_hours } })}
                  </span>
                )}
                {step.completed_at && (
                  <span className="text-slate-500">
                    {t("admin.documents.workflow.completed_at", {
                      values: { datetime: formatDateTime(step.completed_at) ?? "" },
                    })}
                  </span>
                )}
                {overdue && (
                  <span className="rounded bg-rose-100 px-2 py-0.5 text-rose-700">
                    {t("admin.documents.badges.overdue")}
                  </span>
                )}
                {canModify && !isDone && (
                  <button className="btn-secondary btn-xs" onClick={() => onCompleteStep(doc, step.code)}>
                    {t("admin.documents.actions.mark_done")}
                  </button>
                )}
              </div>
              {step.notes && <div className="mt-1 text-slate-500">{step.notes}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
});

