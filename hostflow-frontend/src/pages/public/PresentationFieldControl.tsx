import type { FormPresentationField } from '../../modules/public-intake/types'
import type { LocaleCode } from '../../i18n'
import { intakePresentationFieldLabel } from '../../utils/intakePresentationI18n'
import {
  fieldOptionsForCode,
  isEmptyFieldValue,
  resolveFieldWidget,
  type PresentationFieldValue,
} from '../../utils/intakePresentationFieldOptions'

type TFn = (key: string, options?: { defaultValue?: string }) => string

type Props = {
  field: FormPresentationField & {
    evaluated: NonNullable<FormPresentationField['evaluated']>
  }
  value: PresentationFieldValue | undefined
  error?: string
  disabled?: boolean
  locale: LocaleCode
  t: TFn
  onChange: (qualifiedCode: string, next: PresentationFieldValue) => void
}

export function PresentationFieldControl({ field, value, error, disabled, locale, t, onChange }: Props) {
  const widget = resolveFieldWidget(field)
  const options = fieldOptionsForCode(field.qualified_code, t, locale)
  const required = field.evaluated.intake_level === 'required'
  const label = (
    <span className="mb-1 block text-sm font-medium text-slate-800">
      {intakePresentationFieldLabel(t, field, locale)}
      {required ? <span className="ml-1 text-xs font-normal text-slate-400">({t('public.intake.presentation.required_short', { defaultValue: 'wymagane' })})</span> : null}
    </span>
  )

  if (widget === 'single_select' && options.length > 0) {
    const selected = typeof value === 'string' ? value : ''
    return (
      <fieldset className="block" disabled={disabled || field.evaluated.readonly}>
        {label}
        <div className="space-y-2">
          {options.map((option) => (
            <label key={option.value} className="flex cursor-pointer items-center gap-2.5 text-sm text-slate-700">
              <input
                type="radio"
                name={field.qualified_code}
                className="h-4 w-4 shrink-0 accent-brand-600"
                checked={selected === option.value}
                onChange={() => onChange(field.qualified_code, option.value)}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
        {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
      </fieldset>
    )
  }

  if (widget === 'multi_select' && options.length > 0) {
    const selected = Array.isArray(value) ? value : []
    return (
      <fieldset className="block" disabled={disabled || field.evaluated.readonly}>
        {label}
        <div className="space-y-2">
          {options.map((option) => {
            const checked = selected.includes(option.value)
            return (
              <label key={option.value} className="flex cursor-pointer items-center gap-2.5 text-sm text-slate-700">
                <input
                  type="checkbox"
                  className="h-4 w-4 shrink-0 accent-brand-600"
                  checked={checked}
                  onChange={() => {
                    const next = checked
                      ? selected.filter((item) => item !== option.value)
                      : [...selected, option.value]
                    onChange(field.qualified_code, next)
                  }}
                />
                <span>{option.label}</span>
              </label>
            )
          })}
        </div>
        {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
      </fieldset>
    )
  }

  if (widget === 'textarea') {
    return (
      <label className="block">
        {label}
        <textarea
          className="input min-h-[96px] w-full"
          value={typeof value === 'string' ? value : ''}
          onChange={(e) => onChange(field.qualified_code, e.target.value)}
          disabled={disabled || field.evaluated.readonly}
          readOnly={field.evaluated.readonly}
        />
        {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
      </label>
    )
  }

  const inputType =
    widget === 'email' ? 'email' : widget === 'phone' || widget === 'phone_e164' ? 'tel' : widget === 'date' ? 'date' : widget === 'number' ? 'number' : 'text'

  return (
    <label className="block">
      {label}
      <input
        type={inputType}
        className="input w-full"
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => onChange(field.qualified_code, e.target.value)}
        disabled={disabled || field.evaluated.readonly}
        readOnly={field.evaluated.readonly}
      />
      {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
    </label>
  )
}

export function presentationFieldHasValue(value: PresentationFieldValue | undefined): boolean {
  return !isEmptyFieldValue(value)
}
