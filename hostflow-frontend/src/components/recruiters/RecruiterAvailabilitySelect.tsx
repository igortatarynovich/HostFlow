import type { TranslateFn } from '../../i18n'
import type { RecruiterAvailabilityState } from '../../api/recruiters'

export const RECRUITER_AVAILABILITY_OPTIONS: RecruiterAvailabilityState[] = [
  'available',
  'paused',
  'offline',
  'vacation',
]

type Props = {
  t: TranslateFn
  value: RecruiterAvailabilityState | string
  onChange: (next: RecruiterAvailabilityState) => void
  disabled?: boolean
  className?: string
  'aria-label'?: string
}

export function recruiterAvailabilityLabel(t: TranslateFn, state: string): string {
  const s = String(state || '').toLowerCase()
  const key = `app.recruiters.availability.states.${s}` as const
  const fallback =
    s === 'available'
      ? 'Available'
      : s === 'paused'
        ? 'Paused'
        : s === 'offline'
          ? 'Offline'
          : s === 'vacation'
            ? 'Vacation'
            : state || '—'
  const out = t(key, { defaultValue: fallback })
  return out === key ? fallback : out
}

export function RecruiterAvailabilitySelect({ t, value, onChange, disabled, className, 'aria-label': ariaLabel }: Props) {
  const v = String(value || 'available').toLowerCase()
  return (
    <select
      className={className ?? 'input h-8 max-w-[11rem] py-1 text-xs'}
      value={RECRUITER_AVAILABILITY_OPTIONS.includes(v as RecruiterAvailabilityState) ? v : 'available'}
      disabled={disabled}
      aria-label={ariaLabel}
      onClick={(e) => e.stopPropagation()}
      onChange={(e) => {
        const next = e.target.value as RecruiterAvailabilityState
        if (RECRUITER_AVAILABILITY_OPTIONS.includes(next)) onChange(next)
      }}
    >
      {RECRUITER_AVAILABILITY_OPTIONS.map((opt) => (
        <option key={opt} value={opt}>
          {recruiterAvailabilityLabel(t, opt)}
        </option>
      ))}
    </select>
  )
}
