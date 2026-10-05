import { useCallback, useEffect, useState } from 'react'
import {
  getHrEmployeeRecordSurface,
  updateHrEmployeeRecordCitizenship,
  type HrEmployeeRecordGroup,
  type HrEmployeeRecordRow,
  type HrEmployeeRecordSurface,
  type WorkforceTimelineEvent,
} from '../../api/workforce'
import { useI18n } from '../../i18n'

function formatDay(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [year, month, day] = iso.slice(0, 10).split('-')
  if (!year || !month || !day) return iso
  return `${day}.${month}.${year}`
}

function stateLabel(state: string | null): string {
  if (state === 'preparing') return 'Preparing'
  if (state === 'active') return 'Active'
  if (state === 'ended') return 'Ended'
  return 'No employment'
}

function withTimeline(groups: HrEmployeeRecordGroup[], timeline: WorkforceTimelineEvent[]): HrEmployeeRecordGroup[] {
  return groups.map((group) => {
    if (group.id !== 'historia') return group
    const rows: HrEmployeeRecordRow[] = timeline.slice(0, 8).map((event) => ({
      id: `historia.${event.id}`,
      group: 'historia',
      label: event.title,
      value: event.kind || null,
      status: 'process',
      evidence: null,
      actions: [],
    }))
    return { ...group, rows, empty: rows.length ? null : group.empty }
  })
}

export default function HrEmployeeRecordSurface({
  employeeId,
  manage,
  timeline,
}: {
  employeeId: string
  manage: boolean
  timeline: WorkforceTimelineEvent[]
}) {
  const { t } = useI18n()
  const [surface, setSurface] = useState<HrEmployeeRecordSurface | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [highlight, setHighlight] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    const next = await getHrEmployeeRecordSurface(employeeId)
    setSurface(next)
    return next
  }, [employeeId])

  useEffect(() => {
    let cancelled = false
    setSurface(null)
    setError(null)
    getHrEmployeeRecordSurface(employeeId)
      .then((next) => {
        if (!cancelled) setSurface(next)
      })
      .catch(() => {
        if (!cancelled) {
          setError(t('app.hr.employee_record.load_error', { defaultValue: 'Could not load the employee record.' }))
        }
      })
    return () => {
      cancelled = true
    }
  }, [employeeId, t])

  const openTarget = (target: string | null) => {
    if (!target) return
    setHighlight(target)
    const elementId = target.startsWith('group:') ? `record-group-${target.slice('group:'.length)}` : `record-row-${target}`
    document.getElementById(elementId)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  const saveCitizenship = async () => {
    setSaving(true)
    setError(null)
    try {
      const result = await updateHrEmployeeRecordCitizenship(employeeId, draft)
      if (result.accepted === false) {
        setError(result.reason || t('app.hr.employee_record.save_error', { defaultValue: 'Could not save citizenship.' }))
        return
      }
      setEditing(false)
      await load()
    } catch {
      setError(t('app.hr.employee_record.save_error', { defaultValue: 'Could not save citizenship.' }))
    } finally {
      setSaving(false)
    }
  }

  if (error && !surface) return <p className="text-sm text-rose-800">{error}</p>
  if (!surface) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading…' })}</p>
  }

  const groups = withTimeline(surface.groups, timeline)
  const action = surface.current_process.next_action
  const headerLine = [surface.header.position, surface.header.employer].filter(Boolean).join(' · ')

  return (
    <div className="space-y-4">
      <header className="rounded-xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-950">{surface.header.name}</h2>
        {headerLine ? <p className="mt-1 text-sm text-slate-700">{headerLine}</p> : null}
        <p className="mt-1 text-sm text-slate-600">
          {t('app.hr.driver_surface.employment', { defaultValue: 'Employment' })}: {stateLabel(surface.state)}
          {surface.header.planned_start
            ? ` · ${t('app.hr.driver_surface.planned_start', { defaultValue: 'Planned start' })}: ${formatDay(surface.header.planned_start)}`
            : ''}
        </p>
      </header>

      <section id="hr-verification" className="rounded-xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
        <p className="text-xs font-semibold tracking-wide text-slate-500">
          {t('app.hr.employee_record.current_process', { defaultValue: 'Current process' })}
        </p>
        {action ? (
          <div className="mt-2">
            <p className="text-base font-semibold text-slate-950">
              {t('app.hr.employee_record.next_action', { defaultValue: 'Next action' })}: {action.title}
            </p>
            <p className="mt-1 text-sm text-slate-600">{action.reason}</p>
            <button
              type="button"
              className="mt-3 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white"
              onClick={() => openTarget(surface.current_process.target_row_id)}
            >
              {t('app.hr.employee_record.open', { defaultValue: 'Open' })}
            </button>
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-600">
            {t('app.hr.employee_record.no_action', { defaultValue: 'No open action.' })}
          </p>
        )}
        {error ? <p className="mt-2 text-sm text-rose-800">{error}</p> : null}
      </section>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <p className="border-b border-slate-200 px-4 py-3 text-xs font-semibold tracking-wide text-slate-500">
          {t('app.hr.employee_record.record', { defaultValue: 'Employee record' })}
        </p>
        {groups.map((group) => (
          <div key={group.id} id={`record-group-${group.id}`} className="border-b border-slate-100 last:border-b-0">
            <h3 className="bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-900">{group.label}</h3>
            {group.rows.length === 0 ? (
              <p className="px-4 py-3 text-sm text-slate-500">{emptyLabel(group.empty, t)}</p>
            ) : (
              group.rows.map((row) => (
                <div
                  key={row.id}
                  id={`record-row-${row.id}`}
                  className={`grid grid-cols-1 gap-1 border-t border-slate-100 px-4 py-3 sm:grid-cols-[minmax(9rem,1.1fr)_minmax(8rem,1.2fr)_7rem_7rem_auto] sm:items-center ${
                    highlight === row.id ? 'bg-amber-50' : 'bg-white'
                  }`}
                >
                  <span className="text-sm text-slate-600">{row.label}</span>
                  {editing && row.id === 'dane_osobowe.citizenship' ? (
                    <input
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      aria-label={row.label}
                    />
                  ) : (
                    <span className="text-sm font-medium text-slate-950">{row.value || '—'}</span>
                  )}
                  <span className="text-sm text-slate-600">{row.status}</span>
                  <span className="text-sm text-slate-500">{row.evidence || '—'}</span>
                  <span className="flex gap-2">
                    {row.actions.includes('edit') && manage && row.id === 'dane_osobowe.citizenship' ? (
                      editing ? (
                        <button
                          type="button"
                          className="text-sm font-medium text-slate-900 underline"
                          disabled={saving}
                          onClick={() => void saveCitizenship()}
                        >
                          {t('common.save', { defaultValue: 'Save' })}
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="text-sm font-medium text-slate-900 underline"
                          onClick={() => {
                            setDraft(row.value || '')
                            setEditing(true)
                          }}
                        >
                          {t('app.hr.employee_record.edit', { defaultValue: 'Edit' })}
                        </button>
                      )
                    ) : null}
                  </span>
                </div>
              ))
            )}
          </div>
        ))}
      </section>
    </div>
  )
}

function emptyLabel(reason: string | null, t: (key: string, options?: { defaultValue?: string }) => string): string {
  if (reason === 'not_materialized') {
    return t('app.hr.employee_record.not_materialized', { defaultValue: 'Not materialized' })
  }
  if (reason === 'no_applicable_element') {
    return t('app.hr.employee_record.no_element', { defaultValue: 'No applicable element' })
  }
  if (reason === 'timeline') {
    return t('app.hr.employee_record.no_history', { defaultValue: 'No history yet' })
  }
  return t('app.hr.employee_record.empty', { defaultValue: '—' })
}
