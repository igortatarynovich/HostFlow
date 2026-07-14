import type { FormPresentationRuntime } from '../../modules/public-intake/types'
import type { LocaleCode } from '../../i18n'
import { usePlatformCountryOptions } from '../../hooks/usePlatformCatalogOptions'
import { intakePresentationFieldLabel } from '../../utils/intakePresentationI18n'
import {
  fieldOptionsForCode,
  isEmptyFieldValue,
  resolveFieldWidget,
} from '../../utils/intakePresentationFieldOptions'

type TFn = (key: string, options?: { defaultValue?: string }) => string

type Props = {
  field: FormPresentationRuntime['fields'][number] & { evaluated: { intake_level: string; readonly?: boolean } }
  value: string | string[] | undefined
  error?: string
  disabled?: boolean
  t: TFn
  locale: LocaleCode
  onChange: (qualifiedCode: string, next: string | string[]) => void
}

export default function IntakePresentationField({
  field,
  value,
  error,
  disabled,
  t,
  locale,
  onChange,
}: Props) {
  const widget = resolveFieldWidget(field)
  const countryOptions = usePlatformCountryOptions(locale)
  const defaultOptions = fieldOptionsForCode(field.qualified_code, t, locale)
  const options =
    field.qualified_code === 'platform.identity.citizenship' && countryOptions.length
      ? countryOptions.map((row) => ({ value: row.value, label: row.label }))
      : defaultOptions
  const code = field.qualified_code
  const label = intakePresentationFieldLabel(t, field, locale)
  const required = field.evaluated.intake_level === 'required'

  const stringValue = Array.isArray(value) ? value.join(',') : String(value ?? '')

  if (widget === 'multiselect') {
    const selected = Array.isArray(value) ? value : stringValue ? stringValue.split(',').map((s) => s.trim()).filter(Boolean) : []
    return (
      <label className="block">
        <span className="mb-1 block text-sm font-medium text-slate-700">
          {label}
          {required ? <span className="text-rose-500"> *</span> : null}
        </span>
        <div className="grid gap-2 sm:grid-cols-2">
          {options.map((opt) => {
            const checked = selected.includes(opt.value)
            return (
              <label key={opt.value} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={disabled || field.evaluated.readonly}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...selected, opt.value]
                      : selected.filter((v) => v !== opt.value)
                    onChange(code, next)
                  }}
                />
                <span>{opt.label}</span>
              </label>
            )
          })}
        </div>
        {error ? <span className="mt-1 block text-xs text-rose-600">{error}</span> : null}
      </label>
    )
  }

  if (widget === 'select' || widget === 'yes_no') {
    return (
      <label className="block">
        <span className="mb-1 block text-sm font-medium text-slate-700">
          {label}
          {required ? <span className="text-rose-500"> *</span> : null}
        </span>
        <select
          className="input w-full"
          value={stringValue}
          disabled={disabled || field.evaluated.readonly}
          onChange={(e) => onChange(code, e.target.value)}
        >
          <option value="">{t('public.intake.presentation.select_placeholder', { defaultValue: 'Select…' })}</option>
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error ? <span className="mt-1 block text-xs text-rose-600">{error}</span> : null}
      </label>
    )
  }

  const inputType =
    widget === 'email' ? 'email' : widget === 'phone' ? 'tel' : widget === 'date' ? 'date' : widget === 'number' ? 'number' : 'text'

  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">
        {label}
        {required ? <span className="text-rose-500"> *</span> : null}
      </span>
      <input
        type={inputType}
        className="input w-full"
        value={stringValue}
        disabled={disabled || field.evaluated.readonly}
        readOnly={Boolean(field.evaluated.readonly)}
        onChange={(e) => onChange(code, e.target.value)}
      />
      {error ? <span className="mt-1 block text-xs text-rose-600">{error}</span> : null}
    </label>
  )
}

export function validateVisiblePresentationField(
  field: FormPresentationRuntime['fields'][number] & { evaluated: { intake_level: string; visible: boolean } },
  value: string | string[] | undefined,
): boolean {
  if (!field.evaluated.visible) return true
  if (field.evaluated.intake_level !== 'required') return true
  return !isEmptyFieldValue(value)
}
