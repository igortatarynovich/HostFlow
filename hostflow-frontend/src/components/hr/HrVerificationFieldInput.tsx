import { useMemo } from 'react'
import type { HrDocumentFieldReview } from '../../api/workforce'
import { Combobox } from '../ui/Combobox'
import { buildCountryOptions } from '../../data/countries'
import { useI18n } from '../../i18n'
import { resolveHrFieldInputType } from './hrVerificationFieldMeta'

type Props = {
  field: HrDocumentFieldReview
  value: string
  disabled?: boolean
  onChange: (value: string) => void
}

function normalizeDateValue(value: string): string {
  const raw = value.trim()
  if (!raw) return ''
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw
  const parsed = Date.parse(raw)
  if (Number.isNaN(parsed)) return raw.slice(0, 10)
  return new Date(parsed).toISOString().slice(0, 10)
}

export default function HrVerificationFieldInput({ field, value, disabled, onChange }: Props) {
  const { locale, t } = useI18n()
  const inputType = resolveHrFieldInputType(field)
  const countryOptions = useMemo(() => buildCountryOptions(locale), [locale])

  if (inputType === 'country') {
    return (
      <div className="mt-2">
        <Combobox
          options={countryOptions}
          value={value}
          disabled={disabled}
          placeholder={t('app.hr.verify_field.country_placeholder', { defaultValue: 'Select country' })}
          searchPlaceholder={t('common.search', { defaultValue: 'Search' })}
          noResultsLabel={t('common.no_results', { defaultValue: 'No results' })}
          onChange={onChange}
        />
      </div>
    )
  }

  if (inputType === 'date') {
    return (
      <input
        type="date"
        className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        value={normalizeDateValue(value)}
        aria-label={field.label}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
    )
  }

  const htmlType = inputType === 'email' ? 'email' : inputType === 'tel' ? 'tel' : 'text'

  return (
    <input
      type={htmlType}
      className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      value={value}
      aria-label={field.label}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}
