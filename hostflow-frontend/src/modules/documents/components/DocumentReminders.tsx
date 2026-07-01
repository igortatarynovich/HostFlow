/**
 * Component for displaying document reminders
 */

import { memo } from "react";
import type { DocumentReminder } from "../../../api/types";
import { formatDate } from "../documentUtils";

interface DocumentRemindersProps {
  reminders: DocumentReminder[];
}

export const DocumentReminders = memo(function DocumentReminders({ reminders }: DocumentRemindersProps) {
  if (!reminders.length) return null;

  return (
    <div className="flex flex-wrap gap-2 text-[11px] text-slate-600">
      {reminders.slice(0, 5).map((reminder, idx) => (
        <span
          key={`${reminder.due_at}-${reminder.step_code ?? ""}-${reminder.kind}-${idx}`}
          className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5"
        >
          {reminder.step_code ? `${reminder.step_code} · ` : ""}
          {formatDate(reminder.due_at) || ""}
        </span>
      ))}
    </div>
  );
});

