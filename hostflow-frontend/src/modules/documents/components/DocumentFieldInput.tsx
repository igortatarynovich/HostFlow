/**
 * Component for rendering document field inputs based on field configuration
 */

import { memo } from "react";
import type { DocumentFieldConfig } from "../documentFieldsConfig";
import { getDocumentFieldsConfig } from "../documentFieldsConfig";
import DateInput from "../../../components/controls/DateInput";
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
        <div className="text-xs text-slate-500">{label}</div>
        <input
          className="input"
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
        <div className="text-xs text-slate-500">{label}</div>
        <DateInput
          value={value ? String(value).slice(0, 10) : ""}
          onValueChange={onChange}
          disabled={disabled}
        />
      </label>
    );
  }

  if (fieldConfig.type === "select") {
    return (
      <label className="block">
        <div className="text-xs text-slate-500">{label}</div>
        <select
          className="input"
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
      <label className="col-span-full block">
        <div className="text-xs text-slate-500">{label}</div>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {fieldConfig.options?.map((opt) => {
            const isChecked = selectedValues.includes(opt.value);
            const text = opt.labelKey ? t(opt.labelKey, { defaultValue: opt.label }) : opt.label;
            return (
              <label
                key={opt.value}
                className={`inline-flex h-7 items-center rounded-md border px-2 text-xs ${
                  isChecked
                    ? 'border-brand-300 bg-brand-50 text-slate-900'
                    : 'border-slate-200 bg-white text-slate-600'
                } ${disabled ? 'cursor-default opacity-60' : 'cursor-pointer'}`}
              >
                <input
                  type="checkbox"
                  className="sr-only"
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
                <span>{text}</span>
              </label>
            );
          })}
        </div>
      </label>
    );
  }

  return null;
});
