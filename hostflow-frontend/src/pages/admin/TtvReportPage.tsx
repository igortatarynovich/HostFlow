import { useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { getTtvReport, type TtvReport, type TtvStep } from '../../api/analytics'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'

const ORDER: TtvStep[] = [
  'signup',
  'plan_selected',
  'company_created',
  'first_client_created',
  'first_candidate_created',
  'email_connected',
  'first_email_sent',
]

function formatSeconds(value: number): string {
  if (!Number.isFinite(value) || value < 0) return '—'
  if (value < 60) return `${Math.round(value)}s`
  const minutes = Math.floor(value / 60)
  const seconds = Math.round(value % 60)
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const remMin = minutes % 60
    return `${hours}h ${remMin}m`
  }
  return seconds ? `${minutes}m ${seconds}s` : `${minutes}m`
}

export default function TtvReportPage() {
  const { t } = useI18n()
  const [days, setDays] = useState(30)
  const [report, setReport] = useState<TtvReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await getTtvReport({ days })
        if (!cancelled) setReport(data)
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message || t('admin.ttv.load_error', { defaultValue: 'Failed to load TTV report' }))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [days, t])

  const steps = ORDER.map((key) => report?.steps.find((s) => s.step_key === key) ?? null)

  return (
    <SettingsSubpageHeader
      backLabel={t('admin.settings.subpage.back_all')}
      kicker={t('admin.ttv.header_kicker')}
      title={t('admin.ttv.title', { defaultValue: 'Time To Value (North Star path)' })}
      subtitle={
        <div>
          <p>
            {t('admin.ttv.subtitle', {
              defaultValue: 'Median and p90 times between signup and key milestones (per tenant).',
            })}
          </p>
          {report ? (
            <p className="mt-1 text-xs text-slate-500">
              {t('admin.ttv.actors', {
                defaultValue: 'Actors in sample: {count}',
                values: { count: report.actors },
              })}
            </p>
          ) : null}
        </div>
      }
      actions={
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-600">
            {t('admin.ttv.days_label', { defaultValue: 'Window (days)' })}
          </label>
          <input
            type="number"
            min={1}
            max={180}
            value={days}
            onChange={(e) => {
              const next = Number.parseInt(e.target.value, 10)
              if (!Number.isFinite(next)) return
              setDays(Math.min(180, Math.max(1, next)))
            }}
            className="input h-8 w-20 px-2 py-1 text-xs"
          />
        </div>
      }
    >
      {error && (
        <ErrorRecoveryBanner
          info={{ title: error, hint: t('app.common.retry_hint') }}
          onRetry={() => setDays((d) => d)}
          retryLabel={t('common.actions.refresh')}
        />
      )}
      <section className="card p-6">

        {loading && (
          <p className="text-sm text-slate-500">
            {t('common.loading')}
          </p>
        )}

        {!loading && (
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2 font-medium">
                    {t('admin.ttv.step_label', { defaultValue: 'Step' })}
                  </th>
                  <th className="px-3 py-2 font-medium">
                    {t('admin.ttv.samples', { defaultValue: 'Samples' })}
                  </th>
                  <th className="px-3 py-2 font-medium">
                    {t('admin.ttv.p50', { defaultValue: 'Median (p50)' })}
                  </th>
                  <th className="px-3 py-2 font-medium">
                    {t('admin.ttv.p90', { defaultValue: 'p90' })}
                  </th>
                  <th className="px-3 py-2 font-medium">
                    {t('admin.ttv.min', { defaultValue: 'Min' })}
                  </th>
                  <th className="px-3 py-2 font-medium">
                    {t('admin.ttv.max', { defaultValue: 'Max' })}
                  </th>
                </tr>
              </thead>
              <tbody>
                {ORDER.map((key, index) => {
                  const row = steps[index]
                  const label =
                    key === 'signup'
                      ? t('admin.ttv.step.signup', { defaultValue: 'Signup completed' })
                      : key === 'plan_selected'
                        ? t('admin.ttv.step.plan_selected', { defaultValue: 'Plan selected / checkout started' })
                        : key === 'company_created'
                          ? t('admin.ttv.step.company_created', { defaultValue: 'Operating company created' })
                          : key === 'first_client_created'
                            ? t('admin.ttv.step.first_client_created', { defaultValue: 'First client created' })
                            : key === 'first_candidate_created'
                              ? t('admin.ttv.step.first_candidate_created', { defaultValue: 'First candidate created' })
                              : key === 'email_connected'
                                ? t('admin.ttv.step.email_connected', { defaultValue: 'Email connected' })
                                : t('admin.ttv.step.first_email_sent', { defaultValue: 'First email sent' })
                  return (
                    <tr key={key} className="border-b border-slate-100 last:border-0">
                      <td className="px-3 py-2 text-slate-800">{label}</td>
                      <td className="px-3 py-2 text-slate-700">{row?.samples ?? 0}</td>
                      <td className="px-3 py-2 text-slate-700">
                        {row ? formatSeconds(row.p50_seconds) : '—'}
                      </td>
                      <td className="px-3 py-2 text-slate-700">
                        {row ? formatSeconds(row.p90_seconds) : '—'}
                      </td>
                      <td className="px-3 py-2 text-slate-700">
                        {row ? formatSeconds(row.min_seconds) : '—'}
                      </td>
                      <td className="px-3 py-2 text-slate-700">
                        {row ? formatSeconds(row.max_seconds) : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </SettingsSubpageHeader>
  )
}
