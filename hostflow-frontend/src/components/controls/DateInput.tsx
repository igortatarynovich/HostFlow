import { useState } from 'react'
import { IconCalendar } from '@tabler/icons-react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { useAuthOptional } from '../../store/auth'
import {
  formatSystemDate,
  maskSystemDate,
  normalizeSystemDateFormat,
  parseSystemDate,
  type SystemDateFormat,
} from './systemDate'

type DateInputProps = {
  value?: string | null
  onValueChange: (isoDate: string) => void
  disabled?: boolean
  required?: boolean
  className?: string
  testId?: string
  id?: string
  format?: SystemDateFormat
}

export default function DateInput({
  value,
  onValueChange,
  disabled,
  required,
  className,
  testId,
  id,
  format,
}: DateInputProps) {
  const { t } = useI18n()
  const auth = useAuthOptional()
  const resolved = format ?? normalizeSystemDateFormat(auth?.preferences?.ui?.date_format)
  const iso = formatSystemDate(value, 'YYYY-MM-DD')
  const [editing, setEditing] = useState<string | null>(null)
  const shown = editing ?? formatSystemDate(iso, resolved)

  const commit = (text: string) => {
    setEditing(null)
    const parsed = parseSystemDate(text, resolved)
    if (parsed) {
      if (parsed !== iso) onValueChange(parsed)
      return
    }
    if (!text.trim() && iso) onValueChange('')
  }

  return (
    <div className={clsx('flex min-w-0 items-center gap-1', className)}>
      <input
        id={id}
        data-testid={testId}
        className="input min-w-0 flex-1"
        inputMode="numeric"
        autoComplete="off"
        placeholder={resolved}
        disabled={disabled}
        required={required}
        value={shown}
        onFocus={() => setEditing(formatSystemDate(iso, resolved))}
        onChange={(event) => setEditing(maskSystemDate(event.target.value, resolved))}
        onBlur={(event) => commit(event.currentTarget.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') event.currentTarget.blur()
        }}
      />
      <button
        type="button"
        className="btn-secondary shrink-0 px-2"
        disabled={disabled}
        aria-label={t('common.actions.calendar', { defaultValue: 'Calendar' })}
        onMouseDown={(event) => event.preventDefault()}
        onClick={(event) => {
          const picker = event.currentTarget.nextElementSibling
          if (picker instanceof HTMLInputElement) picker.showPicker?.()
        }}
      >
        <IconCalendar size={16} />
      </button>
      <input
        type="date"
        tabIndex={-1}
        aria-hidden
        className="sr-only"
        value={iso}
        disabled={disabled}
        onChange={(event) => {
          const next = event.target.value
          setEditing(null)
          if (next !== iso) onValueChange(next)
        }}
      />
    </div>
  )
}
