import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { IconCalendar, IconChevronLeft, IconChevronRight } from '@tabler/icons-react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { useAuthOptional } from '../../store/auth'
import { menuBox } from '../ui/comboboxShared'
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

type CivilDate = { year: number; month: number; day: number }

function civilFromIso(iso: string): CivilDate | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  if (!match) return null
  return { year: Number(match[1]), month: Number(match[2]), day: Number(match[3]) }
}

function isoFromCivil(date: CivilDate): string {
  const month = String(date.month).padStart(2, '0')
  const day = String(date.day).padStart(2, '0')
  return `${date.year}-${month}-${day}`
}

function todayCivil(): CivilDate {
  const now = new Date()
  return { year: now.getFullYear(), month: now.getMonth() + 1, day: now.getDate() }
}

function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

function mondayIndex(year: number, month: number): number {
  const weekday = new Date(year, month - 1, 1).getDay()
  return (weekday + 6) % 7
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
  const { t, locale } = useI18n()
  const auth = useAuthOptional()
  const resolved = format ?? normalizeSystemDateFormat(auth?.preferences?.ui?.date_format)
  const iso = formatSystemDate(value, 'YYYY-MM-DD')
  const selected = civilFromIso(iso)
  const [editing, setEditing] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [view, setView] = useState<CivilDate>(() => selected ?? todayCivil())
  const [box, setBox] = useState<ReturnType<typeof menuBox> | null>(null)
  const anchorRef = useRef<HTMLButtonElement | null>(null)
  const panelRef = useRef<HTMLDivElement | null>(null)
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

  const openCalendar = () => {
    if (disabled) return
    setView(selected ?? todayCivil())
    setOpen((current) => !current)
  }

  useLayoutEffect(() => {
    if (!open || !anchorRef.current) return
    const place = () => {
      const anchor = anchorRef.current
      if (!anchor) return
      const placed = menuBox(anchor)
      const width = Math.max(placed.width, 280)
      const left = Math.min(Math.max(8, placed.left - (width - placed.width)), window.innerWidth - width - 8)
      setBox({ ...placed, left, width })
    }
    place()
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    return () => {
      window.removeEventListener('resize', place)
      window.removeEventListener('scroll', place, true)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    function onPointer(event: MouseEvent) {
      const target = event.target as Node
      if (anchorRef.current?.contains(target) || panelRef.current?.contains(target)) return
      setOpen(false)
    }
    function onEsc(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onEsc)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onEsc)
    }
  }, [open])

  const monthLabel = new Intl.DateTimeFormat(locale, { month: 'long', year: 'numeric' }).format(
    new Date(view.year, view.month - 1, 1),
  )
  const weekday = new Intl.DateTimeFormat(locale, { weekday: 'narrow' })
  const weekdays = Array.from({ length: 7 }, (_, index) => weekday.format(new Date(2026, 0, 5 + index)))
  const leading = mondayIndex(view.year, view.month)
  const count = daysInMonth(view.year, view.month)
  const today = todayCivil()

  const shiftMonth = (delta: number) => {
    const next = new Date(view.year, view.month - 1 + delta, 1)
    setView({ year: next.getFullYear(), month: next.getMonth() + 1, day: 1 })
  }

  const panel = open && box ? createPortal(
    <div
      ref={panelRef}
      role="dialog"
      aria-label={t('common.actions.calendar', { defaultValue: 'Calendar' })}
      data-testid="date-input-calendar"
      className="fixed z-20 overflow-auto rounded-xl border border-gray-200 bg-white p-2 shadow-lg"
      style={{ top: box.top, left: box.left, width: box.width, maxHeight: box.maxHeight }}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <button
          type="button"
          className="btn-secondary px-2"
          aria-label={t('common.actions.back', { defaultValue: 'Back' })}
          onClick={() => shiftMonth(-1)}
        >
          <IconChevronLeft size={16} />
        </button>
        <div className="text-sm font-medium capitalize text-slate-900">{monthLabel}</div>
        <button
          type="button"
          className="btn-secondary px-2"
          aria-label={t('common.actions.next', { defaultValue: 'Next' })}
          onClick={() => shiftMonth(1)}
        >
          <IconChevronRight size={16} />
        </button>
      </div>
      <div className="grid grid-cols-7">
        {weekdays.map((label, index) => (
          <div key={`weekday-${index}`} className="py-1 text-center text-xs text-slate-500">{label}</div>
        ))}
        {Array.from({ length: leading }, (_, index) => (
          <div key={`pad-${index}`} />
        ))}
        {Array.from({ length: count }, (_, index) => {
          const day = index + 1
          const active = selected?.year === view.year && selected.month === view.month && selected.day === day
          const isToday = today.year === view.year && today.month === view.month && today.day === day
          return (
            <button
              key={day}
              type="button"
              className={clsx(
                'h-8 rounded-md text-sm',
                active ? 'bg-slate-900 text-white' : 'text-slate-900 hover:bg-slate-50',
                !active && isToday && 'ring-1 ring-slate-300',
              )}
              onClick={() => {
                onValueChange(isoFromCivil({ year: view.year, month: view.month, day }))
                setEditing(null)
                setOpen(false)
              }}
            >
              {day}
            </button>
          )
        })}
      </div>
    </div>,
    document.body,
  ) : null

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
        ref={anchorRef}
        type="button"
        className="btn-secondary shrink-0 px-2"
        disabled={disabled}
        aria-expanded={open}
        aria-label={t('common.actions.calendar', { defaultValue: 'Calendar' })}
        onMouseDown={(event) => event.preventDefault()}
        onClick={openCalendar}
      >
        <IconCalendar size={16} />
      </button>
      {panel}
    </div>
  )
}
