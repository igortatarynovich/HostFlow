/**
 * Component for displaying document workflow steps
 */

import { memo, useEffect, useState } from "react";
import clsx from "clsx";
import type { Document, DocumentWorkflow as DocumentWorkflowState, DocumentWorkflowStep, DocumentStatus } from "../../../api/types";
import { DOCUMENT_STATUS_META } from "../constants";
import { formatDate } from "../documentUtils";
import { isWorkflowStepDone } from "../workflowUtils";
import { useI18n } from "../../../i18n";

interface DocumentWorkflowProps {
  doc: Document;
  workflow: DocumentWorkflowState | undefined;
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
  const [nowMs, setNowMs] = useState<number | null>(null);
  useEffect(() => {
    setNowMs(Date.now());
  }, []);
  const steps = Array.isArray(workflow?.steps) ? workflow!.steps : [];
  if (!steps.length) return null;

  const completed = steps.filter((step) => isWorkflowStepDone(step)).length;
  const total = steps.length;
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;
  const processLabel = translateProcess(workflow?.process_type ?? doc.process_type) ?? doc.process_type;
  const hasActive = steps.some((step) => String(step.status || "").toLowerCase() === "in_progress");
  const unfinishedExists = steps.some((step) => !isWorkflowStepDone(step));
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
          const isDone = isWorkflowStepDone(step);
          const stepTitle =
            t(`documents.workflow.step.${step.code}`, { defaultValue: "" }) || step.title || step.code;
          const badge = DOCUMENT_STATUS_META[step.status as DocumentStatus]?.color ?? "bg-slate-100 text-slate-600";
          const dueAtDate = step.due_at ? new Date(step.due_at) : null;
          const overdue = Boolean(dueAtDate && nowMs !== null && dueAtDate.getTime() < nowMs && !isDone);
          const metaBeforeDue: string[] = [];
          if (step.ordered_at) {
            const d = formatDate(step.ordered_at);
            if (d)
              metaBeforeDue.push(
                t("admin.documents.workflow.ordered_at", { values: { datetime: d } }),
              );
          }
          let dueMeta: string | null = null;
          if (step.due_at) {
            const d = formatDate(step.due_at);
            if (d)
              dueMeta = t("admin.documents.workflow.due_at", { values: { datetime: d } });
          }
          const metaAfterDue: string[] = [];
          if (
            typeof step.due_in_hours === "number" &&
            !Number.isNaN(step.due_in_hours) &&
            !step.due_at
          ) {
            metaAfterDue.push(
              t("admin.documents.workflow.due_in_hours", { values: { hours: step.due_in_hours } }),
            );
          }
          if (step.completed_at) {
            const d = formatDate(step.completed_at);
            if (d)
              metaAfterDue.push(
                t("admin.documents.workflow.completed_at", { values: { datetime: d } }),
              );
          }
          const hasMeta =
            metaBeforeDue.length > 0 || Boolean(dueMeta) || metaAfterDue.length > 0;

          return (
            <div key={step.code} className="rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="font-medium text-slate-700">{stepTitle}</span>
                <span className={clsx("inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5", badge)}>
                  {translateStatus(step.status || rawStatus)}
                </span>
                {hasMeta ? (
                  <span className="min-w-0 tabular-nums">
                    {metaBeforeDue.length > 0 ? (
                      <span className="text-slate-500">{metaBeforeDue.join(" · ")}</span>
                    ) : null}
                    {dueMeta ? (
                      <>
                        {metaBeforeDue.length > 0 ? <span className="text-slate-300"> · </span> : null}
                        <span className={clsx(overdue ? "font-medium text-rose-600" : "text-slate-500")}>
                          {dueMeta}
                        </span>
                      </>
                    ) : null}
                    {metaAfterDue.length > 0 ? (
                      <>
                        {(metaBeforeDue.length > 0 || dueMeta) ? <span className="text-slate-300"> · </span> : null}
                        <span className="text-slate-500">{metaAfterDue.join(" · ")}</span>
                      </>
                    ) : null}
                  </span>
                ) : null}
                {overdue && (
                  <span className="shrink-0 rounded bg-rose-100 px-2 py-0.5 text-rose-700">
                    {t("admin.documents.badges.overdue")}
                  </span>
                )}
                {canModify && !isDone && (
                  <button type="button" className="btn-secondary btn-xs shrink-0" onClick={() => onCompleteStep(doc, step.code)}>
                    {t("admin.documents.actions.mark_done")}
                  </button>
                )}
              </div>
              {step.notes ? (
                <div className="mt-1 line-clamp-2 text-slate-500" title={step.notes}>
                  {step.notes}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
});
