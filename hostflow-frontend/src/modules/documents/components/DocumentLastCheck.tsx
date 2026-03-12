/**
 * Component for displaying document last check information
 */

import { memo } from "react";
import clsx from "clsx";
import type { Document, DocumentCheck } from "../../../api/types";
import { formatDateTime } from "../documentUtils";
import { useI18n } from "../../../i18n";

interface DocumentLastCheckProps {
  check: DocumentCheck | null | undefined;
}

export const DocumentLastCheck = memo(function DocumentLastCheck({ check }: DocumentLastCheckProps) {
  const { t } = useI18n();
  if (!check) return null;

  const badge = check.decision === "approved" ? "bg-green-50 text-green-700" : "bg-rose-50 text-rose-700";
  const decisionLabel =
    check.decision === "approved"
      ? t("admin.documents.badges.approved")
      : t("admin.documents.badges.rejected");

  return (
    <div className="rounded border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
      <div className="flex flex-wrap items-center gap-2">
        <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5", badge)}>
          {decisionLabel}
        </span>
        {check.reviewer_id && (
          <span className="text-slate-500">
            {t("admin.documents.labels.reviewer", { values: { reviewer: check.reviewer_id } })}
          </span>
        )}
        {check.created_at && <span className="text-slate-500">{formatDateTime(check.created_at)}</span>}
      </div>
      {check.comment && <div className="mt-1 text-slate-600">{check.comment}</div>}
    </div>
  );
});

