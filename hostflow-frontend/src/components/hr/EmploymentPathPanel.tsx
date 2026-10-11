import { useCallback, useEffect, useState } from 'react'
import {
  activateEmployment,
  confirmEmploymentTerms,
  fetchEmploymentPath,
  materializeEmploymentRequirements,
  recordEmploymentLegal,
  recordReadyToStart,
  waiveEmploymentRequirement,
  type EmploymentPath,
  type LegalReading,
} from '../../api/hrEmploymentPath'

type Props = { employeeId: string }

const EMPTY_LEGAL: LegalReading = {
  citizenship_class: 'pl',
  stay_basis: 'not_required',
  work_authorization_basis: 'not_required',
  valid_for_this_employment: 'yes',
}

function errorText(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (err instanceof Error && err.message) return err.message
  return 'Request failed'
}

export function EmploymentPathPanel({ employeeId }: Props) {
  const [path, setPath] = useState<EmploymentPath | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [legal, setLegal] = useState<LegalReading>(EMPTY_LEGAL)
  const [dataComplete, setDataComplete] = useState(false)
  const [definitionKey, setDefinitionKey] = useState('operator_check')
  const [waiverReason, setWaiverReason] = useState('operator waiver')
  const [terms, setTerms] = useState({
    position: '',
    contract_basis: 'employment',
    work_time_value: '1',
    work_time_unit: 'full_time',
    workplace: '',
    compensation_amount: '',
    compensation_currency: 'PLN',
    compensation_unit: 'month',
    duration: 'indefinite',
    probation_status: 'none',
  })

  const reload = useCallback(async () => {
    const next = await fetchEmploymentPath(employeeId)
    setPath(next)
    if (next.legal?.citizenship_class) {
      setLegal({
        citizenship_class: next.legal.citizenship_class,
        stay_basis: next.legal.stay_basis || '',
        work_authorization_basis: next.legal.work_authorization_basis || '',
        valid_for_this_employment: next.legal.valid_for_this_employment || '',
      })
    }
    if (next.ready_to_start?.employee_data_result === 'pass') setDataComplete(true)
  }, [employeeId])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    void reload()
      .catch((err) => {
        if (!cancelled) setError(errorText(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [reload])

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true)
    setError(null)
    try {
      await action()
      await reload()
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Employment…</p>
  if (!path?.employment) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
        Трудоустройство ещё не открыто. Примите передачу в HR Inbox — появится Employment (preparing).
      </section>
    )
  }

  const employment = path.employment
  const preparing = employment.state === 'preparing'
  const field = 'w-full rounded-md border border-slate-300 px-2 py-1 text-sm'

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 space-y-4">
      <div>
        <h2 className="text-base font-semibold text-slate-900">Путь до Active</h2>
        <p className="text-sm text-slate-600">Состояние: {employment.state}</p>
      </div>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}

      <div className="grid gap-2 sm:grid-cols-2">
        <label className="text-xs text-slate-600">
          Гражданство
          <input className={field} value={legal.citizenship_class} onChange={(e) => setLegal({ ...legal, citizenship_class: e.target.value })} />
        </label>
        <label className="text-xs text-slate-600">
          Основание пребывания
          <input className={field} value={legal.stay_basis} onChange={(e) => setLegal({ ...legal, stay_basis: e.target.value })} />
        </label>
        <label className="text-xs text-slate-600">
          Основание работы
          <input className={field} value={legal.work_authorization_basis} onChange={(e) => setLegal({ ...legal, work_authorization_basis: e.target.value })} />
        </label>
        <label className="text-xs text-slate-600">
          Действительно для этого трудоустройства
          <input className={field} value={legal.valid_for_this_employment} onChange={(e) => setLegal({ ...legal, valid_for_this_employment: e.target.value })} />
        </label>
      </div>
      <button type="button" className="btn-secondary btn-sm" disabled={busy || !preparing} onClick={() => void run(() => recordEmploymentLegal(employment.id, legal))}>
        Записать Legal {path.legal ? `(${path.legal.outcome})` : ''}
      </button>

      <label className="flex items-center gap-2 text-sm text-slate-800">
        <input type="checkbox" checked={dataComplete} onChange={(e) => setDataComplete(e.target.checked)} />
        Данные сотрудника полные
      </label>

      <div className="grid gap-2 sm:grid-cols-2">
        {(
          [
            ['position', 'Должность'],
            ['contract_basis', 'Основание договора'],
            ['work_time_value', 'Время работы'],
            ['work_time_unit', 'Единица времени'],
            ['workplace', 'Место работы'],
            ['compensation_amount', 'Сумма'],
            ['compensation_currency', 'Валюта'],
            ['compensation_unit', 'Единица оплаты'],
            ['duration', 'Срок (indefinite или fixed)'],
            ['probation_status', 'Испытательный (none или dated)'],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="text-xs text-slate-600">
            {label}
            <input className={field} value={terms[key]} onChange={(e) => setTerms({ ...terms, [key]: e.target.value })} />
          </label>
        ))}
      </div>
      <button
        type="button"
        className="btn-secondary btn-sm"
        disabled={busy || !preparing}
        onClick={() => void run(() => confirmEmploymentTerms(employment.id, terms))}
      >
        Подтвердить условия {path.terms?.complete ? '(complete)' : ''}
      </button>

      <div className="flex flex-wrap items-end gap-2">
        <label className="text-xs text-slate-600">
          Требование
          <input className={field} value={definitionKey} onChange={(e) => setDefinitionKey(e.target.value)} />
        </label>
        <label className="text-xs text-slate-600">
          Причина отказа от требования
          <input className={field} value={waiverReason} onChange={(e) => setWaiverReason(e.target.value)} />
        </label>
        <button type="button" className="btn-secondary btn-sm" disabled={busy || !preparing} onClick={() => void run(() => materializeEmploymentRequirements(employment.id, definitionKey))}>
          Зафиксировать набор
        </button>
        <button type="button" className="btn-secondary btn-sm" disabled={busy || !preparing} onClick={() => void run(() => waiveEmploymentRequirement(employment.id, definitionKey, waiverReason))}>
          Снять требование
        </button>
      </div>
      {path.requirements && path.requirements.length > 0 ? (
        <ul className="text-sm text-slate-700">
          {path.requirements.map((row) => (
            <li key={row.definition_key}>
              {row.definition_key}: {row.applicability} / {row.resolution || '—'}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">Набор требований ещё не зафиксирован.</p>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="btn-secondary btn-sm"
          disabled={busy || !preparing}
          onClick={() => void run(() => recordReadyToStart(employment.id, legal, dataComplete))}
        >
          Ready to Start {path.ready_to_start ? `(${path.ready_to_start.outcome})` : ''}
        </button>
        <button
          type="button"
          className="btn-primary btn-sm"
          disabled={busy || !preparing || path.ready_to_start?.outcome !== 'pass'}
          onClick={() => void run(() => activateEmployment(employment.id, legal, dataComplete))}
        >
          Сделать Active
        </button>
      </div>
      {path.ready_to_start?.outcome === 'blocked' ? (
        <p className="text-sm text-amber-800">{path.ready_to_start.blocked_reasons}</p>
      ) : null}
    </section>
  )
}
