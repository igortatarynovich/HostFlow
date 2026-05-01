/**
 * Component for displaying document last check information
 */

import { memo } from "react";
import clsx from "clsx";
import type { DocumentCheck } from "../../../api/types";
import { formatDateTime } from "../documentUtils";
import { useI18n } from "../../../i18n";

interface DocumentLastCheckProps {
  check: DocumentCheck | null | undefined;
  /** `inline` — одна строка без рамки (карточки в списке). `card` — отдельный блок. */
  variant?: "card" | "inline";
  className?: string;
}

export const DocumentLastCheck = memo(function DocumentLastCheck({
  check,
  variant = "card",
  className,
}: DocumentLastCheckProps) {
  const { t } = useI18n();
  if (!check) return null;

  const badge = check.decision === "approved" ? "bg-green-50 text-green-700" : "bg-rose-50 text-rose-700";
  const decisionLabel =
    check.decision === "approved"
      ? t("admin.documents.badges.approved")
      : t("admin.documents.badges.rejected");

  const pill = (
    <span className={clsx("inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5", badge)}>
      {decisionLabel}
    </span>
  );

  if (variant === "inline") {
    return (
      <div
        className={clsx(
          "flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-slate-600",
          className,
        )}
      >
        {pill}
        {check.created_at ? <span className="text-slate-500">{formatDateTime(check.created_at)}</span> : null}
        {check.comment ? (
          <span className="min-w-0 max-w-full truncate text-slate-500" title={check.comment}>
            {check.comment}
          </span>
        ) : null}
      </div>
    );
  }

  return (
    <div className={clsx("rounded border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600", className)}>
      <div className="flex flex-wrap items-center gap-2">
        {pill}
        {check.created_at && <span className="text-slate-500">{formatDateTime(check.created_at)}</span>}
      </div>
      {check.comment && <div className="mt-1 text-slate-600">{check.comment}</div>}
    </div>
  );
});

