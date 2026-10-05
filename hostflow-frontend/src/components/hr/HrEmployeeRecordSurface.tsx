import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getHrEmployeeRecordSurface,
  updateHrEmployeeRecordCitizenship,
  type HrEmployeeRecordSurface,
} from '../../api/workforce'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { getRegionDisplayName } from '../../utils/catalogLocale'

const HIDDEN_STATUS = new Set(['recorded', 'missing', 'canonical', 'process'])
const VALUE_LABELS: Record<string, string> = {
  karta_pobytu: 'Residence card',
  visa_d: 'Visa D',
  visa_c: 'Visa C',
  visa_free: 'Visa-free',
  waiting_for_trc: 'Waiting for a residence card',
  special_protection: 'Special protection',
  none: '—',
  separate_required: 'Separate authorization',
  included_in_stay: 'Included in the stay',
  not_required: 'Not required',
  operator_verification: 'Needs verification',
  yes: 'Yes',
  no: '—',
}

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

function looksTechnical(value: string): boolean {
  const trimmed = value.trim()
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) return true
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(trimmed)
}

function displayValue(value: string | null, label: string, locale: 'en' | 'ru' | 'pl'): string {
  if (!value) return '—'
  if (looksTechnical(value)) return '—'
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) return formatDay(value)
  const mapped = VALUE_LABELS[value]
  if (mapped) return mapped
  if (label === 'Obywatelstwo' && value.trim().length === 2) return getRegionDisplayName(value, locale)
  return value
}

function displayStatus(status: string): string | null {
  if (HIDDEN_STATUS.has(status)) return null
  if (status === 'not_applicable') return 'Not required'
  if (status === 'satisfied') return 'Verified'
  if (status === 'unresolved') return 'To verify'
  if (status === 'pending') return 'Pending'
  if (status === 'blocking') return 'Blocking'
  if (status === 'waived') return 'Waived'
  if (status === 'current') return 'Current'
  return null
}

export default function HrEmployeeRecordSurface({
  employeeId,
  manage,
}: {
  employeeId: string
  manage: boolean
}) {
  const { t, locale } = useI18n()
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

  const groups = surface.groups
  const action = surface.current_process.next_action
  const recruitmentHref = surface.candidate_id
    ? `${CRM_APP_PATHS.candidates}/${encodeURIComponent(surface.candidate_id)}`
    : null
  const headerLine = [surface.header.position, surface.header.employer].filter(Boolean).join(' · ')

  return (
    <div className="card min-w-0 space-y-4 p-3">
      <header className="mb-4">
        <h2 className="text-xl font-semibold text-slate-950">{surface.header.name}</h2>
        {headerLine ? <p className="mt-1 text-sm text-slate-700">{headerLine}</p> : null}
        <p className="mt-1 text-sm text-slate-600">
          {t('app.hr.driver_surface.employment', { defaultValue: 'Employment' })}: {stateLabel(surface.state)}
          {surface.header.planned_start
            ? ` · ${t('app.hr.driver_surface.planned_start', { defaultValue: 'Planned start' })}: ${formatDay(surface.header.planned_start)}`
            : ''}
        </p>
      </header>

      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,7fr)_minmax(280px,3fr)] lg:items-start">
        <div className="min-w-0 space-y-4 lg:pr-6">
          {groups.map((group) => (
            <section
              key={group.id}
              id={`record-group-${group.id}`}
              className="rounded-2xl border border-slate-200 bg-white p-4"
            >
              <h3 className="text-sm font-semibold text-slate-900">{group.label}</h3>
              {group.rows.length === 0 ? (
                <p className="mt-4 text-sm text-slate-500">{emptyLabel(group.empty, t)}</p>
              ) : (
                <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
                  {group.rows.map((row) => {
                    const status = displayStatus(row.status)
                    const evidence = row.evidence && !looksTechnical(row.evidence) ? row.evidence : null
                    return (
                      <div
                        key={row.id}
                        id={`record-row-${row.id}`}
                        className={highlight === row.id ? 'rounded-lg bg-amber-50 p-2' : undefined}
                      >
                        <div className="text-xs text-slate-500">{row.label}</div>
                        {editing && row.id === 'dane_osobowe.citizenship' ? (
                          <input
                            className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                            value={draft}
                            onChange={(event) => setDraft(event.target.value)}
                            aria-label={row.label}
                          />
                        ) : (
                          <p className="mt-1 text-sm font-medium text-slate-950">
                            {displayValue(row.value, row.label, locale)}
                          </p>
                        )}
                        {status || evidence ? (
                          <p className="mt-1 text-xs text-slate-500">{[status, evidence].filter(Boolean).join(' · ')}</p>
                        ) : null}
                        {row.actions.includes('edit') && manage && row.id === 'dane_osobowe.citizenship' ? (
                          editing ? (
                            <button
                              type="button"
                              className="mt-1 text-xs font-medium text-slate-900 underline"
                              disabled={saving}
                              onClick={() => void saveCitizenship()}
                            >
                              {t('common.save', { defaultValue: 'Save' })}
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="mt-1 text-xs font-medium text-slate-900 underline"
                              onClick={() => {
                                setDraft(row.value || '')
                                setEditing(true)
                              }}
                            >
                              {t('app.hr.employee_record.edit', { defaultValue: 'Edit' })}
                            </button>
                          )
                        ) : null}
                      </div>
                    )
                  })}
                </div>
              )}
            </section>
          ))}
        </div>
        <aside
          id="hr-verification"
          data-employee-control-rail
          className="min-w-0 lg:sticky lg:top-4 lg:max-h-[calc(100dvh-3.5rem)] lg:overflow-y-auto"
        >
          <section className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-xs font-semibold tracking-wide text-slate-500">
              {t('app.hr.employee_record.current_process', { defaultValue: 'Current process' })}
            </p>
            {action ? (
              <div className="mt-2">
                <p className="text-base font-semibold text-slate-950">{action.title}</p>
                <p className="mt-1 text-sm text-slate-600">{action.reason}</p>
                {surface.current_process.destination === 'recruitment' && recruitmentHref ? (
                  <Link
                    to={recruitmentHref}
                    className="mt-3 inline-block rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white"
                  >
                    {t('app.hr.employee_record.open_recruitment', { defaultValue: 'Open recruitment case' })}
                  </Link>
                ) : (
                  <button
                    type="button"
                    className="mt-3 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white"
                    onClick={() => openTarget(surface.current_process.target_row_id)}
                  >
                    {t('app.hr.employee_record.open', { defaultValue: 'Open' })}
                  </button>
                )}
              </div>
            ) : (
              <p className="mt-2 text-sm text-slate-600">
                {t('app.hr.employee_record.no_action', { defaultValue: 'No open action.' })}
              </p>
            )}
            {error ? <p className="mt-2 text-sm text-rose-800">{error}</p> : null}
          </section>
        </aside>
      </div>
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
