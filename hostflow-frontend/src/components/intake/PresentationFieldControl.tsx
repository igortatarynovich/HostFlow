import type { FormPresentationField } from '../../modules/public-intake/types'
import type { FieldOption } from '../../utils/serviceSalesFieldOptions'

type Props = {
  field: FormPresentationField & { options?: FieldOption[] }
  value: string | string[]
  error?: string
  disabled?: boolean
  onChange: (next: string | string[]) => void
}

function fieldKind(field: FormPresentationField): string {
  return String(field.widget_hint || field.field_type || 'text').toLowerCase()
}

export function PresentationFieldControl({ field, value, error, disabled, onChange }: Props) {
  const kind = fieldKind(field)
  const options = field.options ?? []

  if (kind.includes('multi_select')) {
    const selected = Array.isArray(value) ? value : value ? [value] : []
    return (
      <div className="space-y-2">
        {options.map((opt) => {
          const checked = selected.includes(opt.value)
          return (
            <label key={opt.value} className="flex items-start gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={checked}
                disabled={disabled}
                onChange={(event) => {
                  const next = new Set(selected)
                  if (event.target.checked) next.add(opt.value)
                  else next.delete(opt.value)
                  onChange(Array.from(next))
                }}
              />
              <span>{opt.label}</span>
            </label>
          )
        })}
        {error ? <span className="block text-xs text-red-600">{error}</span> : null}
      </div>
    )
  }

  if (kind.includes('single_select') || kind.includes('select')) {
    if (options.length <= 4) {
      return (
        <div className="space-y-2">
          {options.map((opt) => (
            <label key={opt.value} className="flex items-start gap-2 text-sm text-slate-700">
              <input
                type="radio"
                name={field.qualified_code}
                className="mt-0.5"
                checked={String(value || '') === opt.value}
                disabled={disabled}
                onChange={() => onChange(opt.value)}
              />
              <span>{opt.label}</span>
            </label>
          ))}
          {error ? <span className="block text-xs text-red-600">{error}</span> : null}
        </div>
      )
    }
    return (
      <>
        <select
          className="input w-full"
          value={Array.isArray(value) ? value[0] || '' : String(value || '')}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">—</option>
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
      </>
    )
  }

  if (kind.includes('textarea')) {
    return (
      <>
        <textarea
          className="input w-full min-h-[96px]"
          value={Array.isArray(value) ? value.join(', ') : String(value || '')}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
        />
        {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
      </>
    )
  }

  const inputType = (() => {
    if (kind.includes('email')) return 'email'
    if (kind.includes('phone') || kind.includes('tel')) return 'tel'
    if (kind.includes('date')) return 'date'
    if (kind.includes('number')) return 'number'
    return 'text'
  })()

  return (
    <>
      <input
        type={inputType}
        className="input w-full"
        value={Array.isArray(value) ? value.join(', ') : String(value || '')}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
      {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
    </>
  )
}
