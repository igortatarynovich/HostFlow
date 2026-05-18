import { useMemo, useState } from 'react'
import type { HrReviewPanel, HrVerifiedField } from '../../api/workforce'
import { postHrVerifiedFieldOverride } from '../../api/workforce'

type Props = {
  panel: HrReviewPanel
  employeeId?: string
  handoffId?: string
  manage?: boolean
  onPanelUpdated?: (panel: HrReviewPanel) => void
}

const STATUS_LABEL: Record<string, string> = {
  pending: 'Pending',
  verified: 'Verified',
  conflict: 'Conflict',
  overridden: 'Overridden',
}

function statusClass(status: string): string {
  switch (status) {
    case 'verified':
    case 'overridden':
      return 'bg-emerald-50 text-emerald-800 ring-emerald-200'
    case 'conflict':
      return 'bg-amber-50 text-amber-900 ring-amber-200'
    default:
      return 'bg-slate-50 text-slate-700 ring-slate-200'
  }
}

export default function HrVerifiedFieldsPanel({
  panel,
  employeeId,
  handoffId,
  manage = false,
  onPanelUpdated,
}: Props) {
  const fields = panel.verified_fields ?? []
  const summary = panel.verified_fields_summary
  const critical = useMemo(() => fields.filter((f) => f.is_critical), [fields])
  const [overrideTarget, setOverrideTarget] = useState<HrVerifiedField | null>(null)
  const [overrideValue, setOverrideValue] = useState('')
  const [overrideReason, setOverrideReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!critical.length) {
    return null
  }

  const canOverride = (f: HrVerifiedField) =>
    manage && (f.status === 'pending' || f.status === 'conflict')

  const submitOverride = async () => {
    if (!overrideTarget || (!employeeId && !handoffId)) return
    setBusy(true)
    setError(null)
    try {
      const next = await postHrVerifiedFieldOverride({
        employeeId,
        handoffId,
        fieldCode: overrideTarget.field_code,
        verified_value: overrideValue.trim(),
        override_reason: overrideReason.trim(),
      })
      onPanelUpdated?.(next)
      setOverrideTarget(null)
      setOverrideValue('')
      setOverrideReason('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Override failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section id="hr-verified-fields" className="scroll-mt-24 space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Verified employment data</h2>
          <p className="mt-1 text-sm text-slate-600">
            Source of truth for contracts, ZUS, and payroll — populated when you verify documents.
          </p>
        </div>
        {summary ? (
          <p className="text-xs text-slate-500">
            Critical: {summary.critical_verified}/{summary.critical_total} ready
            {summary.ready ? '' : ' · approval blocked until complete'}
          </p>
        ) : null}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">Field</th>
              <th className="px-4 py-2">Value</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Source</th>
              {manage ? <th className="w-24 px-4 py-2" /> : null}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {critical.map((f) => (
              <tr key={f.id}>
                <td className="px-4 py-3 font-medium text-slate-900">{f.field_label}</td>
                <td className="px-4 py-3 text-slate-800">
                  {f.verified_value || <span className="text-slate-400">—</span>}
                  {f.conflict_reason ? (
                    <p className="mt-1 text-xs text-amber-800">{f.conflict_reason}</p>
                  ) : null}
                  {f.override_reason ? (
                    <p className="mt-1 text-xs text-slate-500">Override: {f.override_reason}</p>
                  ) : null}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${statusClass(f.status)}`}
                  >
                    {STATUS_LABEL[f.status] ?? f.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-600">{f.source_document_key || '—'}</td>
                {manage ? (
                  <td className="px-4 py-3">
                    {canOverride(f) ? (
                      <button
                        type="button"
                        className="text-xs font-medium text-brand-700 hover:underline"
                        onClick={() => {
                          setOverrideTarget(f)
                          setOverrideValue(f.verified_value ?? '')
                          setOverrideReason('')
                          setError(null)
                        }}
                      >
                        Override
                      </button>
                    ) : null}
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {overrideTarget ? (
        <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-medium text-slate-900">Override: {overrideTarget.field_label}</p>
          <label className="block text-xs text-slate-600">
            Verified value
            <input
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={overrideValue}
              onChange={(e) => setOverrideValue(e.target.value)}
            />
          </label>
          <label className="block text-xs text-slate-600">
            Reason (required for audit)
            <textarea
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              rows={2}
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
            />
          </label>
          {error ? <p className="text-xs text-red-600">{error}</p> : null}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={busy || !overrideValue.trim() || !overrideReason.trim()}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              onClick={() => void submitOverride()}
            >
              Save override
            </button>
            <button
              type="button"
              className="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-200"
              onClick={() => setOverrideTarget(null)}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </section>
  )
}
