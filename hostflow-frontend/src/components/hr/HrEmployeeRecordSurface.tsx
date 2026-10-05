import { useCallback, useEffect, useState } from 'react'
import {
  getHrEmployeeRecord,
  patchHrEmployeeRecord,
  type HrEmployeeRecord,
  type HrEmployeeRecordField,
} from '../../api/workforce'

function isScalar(value: unknown): value is string | number | boolean | null {
  return value == null || ['string', 'number', 'boolean'].includes(typeof value)
}

function display(value: unknown): string {
  if (value == null || value === '') return '—'
  if (isScalar(value)) return String(value)
  return JSON.stringify(value)
}

function FieldRow({
  field,
  saving,
  onSave,
  onVerify,
}: {
  field: HrEmployeeRecordField
  saving: boolean
  onSave: (address: string, value: string) => void
  onVerify: (evidenceId: string) => void
}) {
  const [draft, setDraft] = useState(isScalar(field.value) && field.value != null ? String(field.value) : '')
  useEffect(() => {
    setDraft(isScalar(field.value) && field.value != null ? String(field.value) : '')
  }, [field.value])

  const evidenceRows = field.address === 'evidence.rows' && Array.isArray(field.value) ? field.value : null

  return (
    <div className="grid grid-cols-1 gap-1 border-b border-slate-100 py-2 sm:grid-cols-[16rem_minmax(0,1fr)_auto] sm:items-center">
      <div className="text-xs font-medium text-slate-500">{field.address}</div>
      <div className="min-w-0 text-sm text-slate-900">
        {evidenceRows ? (
          <ul className="space-y-1">
            {evidenceRows.length === 0 ? <li>—</li> : null}
            {evidenceRows.map((row) => {
              const item = row as { id?: string; requirement_code?: string; status?: string; document_codes?: string[] }
              return (
                <li key={item.id} className="flex flex-wrap items-center gap-2">
                  <span>
                    {item.requirement_code} · {item.status} · {(item.document_codes || []).join(', ') || '—'}
                  </span>
                  {field.act === 'verify' && item.id && item.status !== 'approved' ? (
                    <button
                      type="button"
                      className="rounded border border-slate-300 px-2 py-0.5 text-xs"
                      disabled={saving}
                      onClick={() => onVerify(item.id!)}
                    >
                      Verify
                    </button>
                  ) : null}
                </li>
              )
            })}
          </ul>
        ) : (
          display(field.value)
        )}
      </div>
      {field.act === 'edit' && isScalar(field.value) ? (
        <form
          className="flex gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            onSave(field.address, draft)
          }}
        >
          <input
            aria-label={field.address}
            className="w-40 rounded border border-slate-300 px-2 py-1 text-sm"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
          <button type="submit" className="rounded bg-slate-900 px-2 py-1 text-xs text-white" disabled={saving}>
            Save
          </button>
        </form>
      ) : (
        <span className="text-xs uppercase text-slate-400">{field.act}</span>
      )}
    </div>
  )
}

export function HrEmployeeRecordSurface({ employeeId }: { employeeId: string }) {
  const [record, setRecord] = useState<HrEmployeeRecord | null>(null)
  const [employmentId, setEmploymentId] = useState<string | undefined>()
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async (nextEmploymentId?: string) => {
    setError(null)
    try {
      const next = await getHrEmployeeRecord(employeeId, nextEmploymentId)
      setRecord(next)
      setEmploymentId(next.employment_id)
    } catch {
      setError('employee_record_unavailable')
    }
  }, [employeeId])

  useEffect(() => {
    void load(undefined)
  }, [load])

  const save = async (address: string, value: string) => {
    if (!record) return
    setSaving(true)
    try {
      const next = await patchHrEmployeeRecord(employeeId, record.employment_id, { address, value })
      setRecord(next)
    } catch {
      setError('employee_record_write_failed')
    } finally {
      setSaving(false)
    }
  }

  const verify = async (evidenceId: string) => {
    if (!record) return
    setSaving(true)
    try {
      const next = await patchHrEmployeeRecord(employeeId, record.employment_id, {
        address: 'evidence.status',
        value: 'approved',
        evidence_id: evidenceId,
      })
      setRecord(next)
    } catch {
      setError('employee_record_write_failed')
    } finally {
      setSaving(false)
    }
  }

  if (error && !record) {
    return <p className="text-sm text-red-700">{error}</p>
  }
  if (!record) {
    return <p className="text-sm text-slate-500">…</p>
  }

  return (
    <section id="hr-employee-record" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm" data-testid="hr-employee-record">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-slate-900">Employee record</h2>
        {record.employments.length > 1 ? (
          <label className="text-sm text-slate-600">
            Employment
            <select
              className="ml-2 rounded border border-slate-300 px-2 py-1"
              value={record.employment_id}
              onChange={(event) => void load(event.target.value)}
            >
              {record.employments.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.id} · {row.state}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>
      {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}
      <div className="space-y-4">
        {record.sections.map((section) => (
          <section key={section.key} data-section={section.key} className="rounded-lg border border-slate-200">
            <h3 className="border-b border-slate-100 px-3 py-2 text-sm font-semibold text-slate-900">{section.label}</h3>
            <div className="px-3">
              {section.fields.map((field) => (
                <FieldRow key={field.address} field={field} saving={saving} onSave={save} onVerify={verify} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  )
}
