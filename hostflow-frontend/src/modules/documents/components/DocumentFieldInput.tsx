/**
 * Component for rendering document field inputs based on field configuration
 */

import { memo } from "react";
import type { DocumentFieldConfig } from "../documentFieldsConfig";
import DateInput from "../../../components/controls/DateInput";
import { ChipFieldEditor } from "../../../components/ui/ChipFieldEditor";
import { useI18n } from "../../../i18n";

interface DocumentFieldInputProps {
  fieldConfig: DocumentFieldConfig;
  value: any;
  onChange: (value: any) => void;
  disabled: boolean;
  /** Row chrome already shows the label. The control is only the editor. */
  bare?: boolean;
}

export const DocumentFieldInput = memo(function DocumentFieldInput({
  fieldConfig,
  value,
  onChange,
  disabled,
  bare = false,
}: DocumentFieldInputProps) {
  const { t } = useI18n();
  const label =
    fieldConfig.labelKey
      ? t(fieldConfig.labelKey, { defaultValue: fieldConfig.label })
      : fieldConfig.label;
  const optionLabel = (opt: { label: string; labelKey?: string }) =>
    opt.labelKey ? t(opt.labelKey, { defaultValue: opt.label }) : opt.label;
  if (fieldConfig.type === "text") {
    const input = (
      <input
        className={bare ? "input" : "input input-sm mt-1"}
        type="text"
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        aria-label={bare ? label : undefined}
      />
    );
    if (bare) return input;
    return (
      <label className="block">
        <div className="text-[11px] text-slate-500">{label}</div>
        {input}
      </label>
    );
  }

  if (fieldConfig.type === "date") {
    const input = (
      <DateInput
        className={bare ? undefined : "mt-1"}
        value={value ? String(value).slice(0, 10) : ""}
        onValueChange={onChange}
        disabled={disabled}
      />
    );
    if (bare) return input;
    return (
      <label className="block">
        <div className="text-[11px] text-slate-500">{label}</div>
        {input}
      </label>
    );
  }

  if (fieldConfig.type === "select") {
    const input = (
      <select
        className={bare ? "input" : "input input-sm mt-1"}
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        aria-label={bare ? label : undefined}
      >
        <option value="">—</option>
        {fieldConfig.options?.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {optionLabel(opt)}
          </option>
        ))}
      </select>
    );
    if (bare) return input;
    return (
      <label className="block">
        <div className="text-[11px] text-slate-500">{label}</div>
        {input}
      </label>
    );
  }

  if (fieldConfig.type === "multiselect") {
    const selectedValues = Array.isArray(value) ? value : [];
    if (bare) {
      return (
        <ChipFieldEditor
          options={(fieldConfig.options || []).map((opt) => ({ value: opt.value, label: optionLabel(opt) }))}
          values={selectedValues}
          onChange={onChange}
          disabled={disabled}
          addLabel={t("common.actions.add")}
          dismissLabel={t("common.actions.dismiss")}
        />
      );
    }
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
                      onChange(selectedValues.filter((v: string) => v !== opt.value));
                    }
                  }}
                  disabled={disabled}
                />
                <span>{optionLabel(opt)}</span>
              </label>
            );
          })}
        </div>
      </label>
    );
  }

  return null;
});
