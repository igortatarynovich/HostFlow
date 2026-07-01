/**
 * Component for rendering document field inputs based on field configuration
 */

import { memo } from "react";
import type { DocumentFieldConfig } from "../documentFieldsConfig";
import { getDocumentFieldsConfig } from "../documentFieldsConfig";
import { useI18n } from "../../../i18n";

interface DocumentFieldInputProps {
  fieldConfig: DocumentFieldConfig;
  value: any;
  onChange: (value: any) => void;
  disabled: boolean;
}

export const DocumentFieldInput = memo(function DocumentFieldInput({
  fieldConfig,
  value,
  onChange,
  disabled,
}: DocumentFieldInputProps) {
  const { t } = useI18n();
  const label =
    fieldConfig.labelKey
      ? t(fieldConfig.labelKey, { defaultValue: fieldConfig.label })
      : fieldConfig.label;
  if (fieldConfig.type === "text") {
    return (
      <label className="block">
        <div className="text-[11px] text-slate-500">{label}</div>
        <input
          className="input input-sm mt-1"
          type="text"
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        />
      </label>
    );
  }

  if (fieldConfig.type === "date") {
    return (
      <label className="block">
        <div className="text-[11px] text-slate-500">{label}</div>
        <input
          className="input input-sm mt-1"
          type="date"
          value={value ? String(value).slice(0, 10) : ""}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        />
      </label>
    );
  }

  if (fieldConfig.type === "select") {
    return (
      <label className="block">
        <div className="text-[11px] text-slate-500">{label}</div>
        <select
          className="input input-sm mt-1"
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        >
          <option value="">—</option>
          {fieldConfig.options?.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.labelKey ? t(opt.labelKey, { defaultValue: opt.label }) : opt.label}
            </option>
          ))}
        </select>
      </label>
    );
  }

  if (fieldConfig.type === "multiselect") {
    const selectedValues = Array.isArray(value) ? value : [];
    return (
      <label className="block">
        <div className="text-[11px] text-slate-500">{label}</div>
        <div className="mt-1 space-y-1">
          {fieldConfig.options?.map((opt) => {
            const isChecked = selectedValues.includes(opt.value);
            return (
              <label key={opt.value} className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300"
                  checked={isChecked}
                  onChange={(e) => {
                    if (e.target.checked) {
                      onChange([...selectedValues, opt.value]);
                    } else {
                      onChange(selectedValues.filter((v) => v !== opt.value));
                    }
                  }}
                  disabled={disabled}
                />
                <span>{opt.labelKey ? t(opt.labelKey, { defaultValue: opt.label }) : opt.label}</span>
              </label>
            );
          })}
        </div>
      </label>
    );
  }

  return null;
});
