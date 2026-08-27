import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowRight, IconChevronRight } from '@tabler/icons-react'
import { getLeadDistribution, patchLeadDistribution, type LeadDistributionOut } from '../api/leadsDistribution'
import { useI18n } from '../i18n'
import { ACTIVATION_PATHS } from '../app/activationRoutes'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
function statusDot(status: string) {
  if (status === 'available') return '🟢'
  if (status === 'busy') return '🟡'
  return '🔴'
}

function reasonLabel(code: string, t: (k: string) => string) {
  const map: Record<string, string> = {
    active_working_hours: t('app.leads.distribution.why.hours'),
    lowest_workload: t('app.leads.distribution.why.workload'),
    language_match: t('app.leads.distribution.why.language'),
  }
  return map[code] || code
}

export default function LeadsDistributionPage() {
  const { t } = useI18n()
  const [data, setData] = useState<LeadDistributionOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await getLeadDistribution()
      setData(d)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const setMode = async (mode: 'automatic' | 'manual') => {
    if (!data) return
    if (mode === 'automatic' && !data.feature_gate.automatic_allowed) return
    setSaving(true)
    try {
      const d = await patchLeadDistribution({ mode })
      setData(d)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (loading || !data) {
    return (
      <PageShell>
        <PageShellHeader>
          <PageHeader
            title={t('app.leads.distribution.title')}
            subtitle={t('app.leads.distribution.subtitle')}
            kind="browse"
          />
        </PageShellHeader>
        <div className="px-4 pb-4 text-sm text-slate-600">
          {loading ? t('common.loading') : error || '—'}
        </div>
      </PageShell>
    )
  }

  const solo = data.team.length <= 1
  const assignmentExplainLines =
    data.next_preview?.detail_lines && data.next_preview.detail_lines.length > 0
      ? data.next_preview.detail_lines
      : data.assignment_detail_lines ?? []

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.leads.distribution.title')}
          subtitle={t('app.leads.distribution.subtitle')}
          kind="browse"
          secondaryActions={
            <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={loading}>
              {t('common.actions.refresh', { defaultValue: 'Refresh' })}
            </button>
          }
        />
      </PageShellHeader>
      <div className="mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col gap-6 overflow-y-auto pb-4">

      {error ? <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">{String(error)}</div> : null}

      {solo && data.mode === 'manual' ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800">
          <div className="font-medium">{t('app.leads.distribution.solo.title')}</div>
          <p className="mt-1 text-slate-600">
            {t('app.leads.distribution.solo.body')}
          </p>
          <Link className="mt-2 inline-block text-sm font-medium text-brand-700 hover:underline" to={`${ACTIVATION_PATHS.billing}?focus=plan`}>
            {t('app.leads.distribution.solo.cta')}
          </Link>
        </div>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          {t('app.leads.distribution.mode.title')}
        </h2>
        <div className="mt-3 flex flex-wrap gap-4">
          <label className="inline-flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="radio"
              name="dist_mode"
              checked={data.mode === 'automatic'}
              disabled={saving || !data.feature_gate.automatic_allowed}
              onChange={() => void setMode('automatic')}
            />
            <span>{t('app.leads.distribution.mode.auto')}</span>
          </label>
          <label className="inline-flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="radio"
              name="dist_mode"
              checked={data.mode === 'manual'}
              disabled={saving}
              onChange={() => void setMode('manual')}
            />
            <span>{t('app.leads.distribution.mode.manual')}</span>
          </label>
        </div>
        {!data.feature_gate.automatic_allowed ? (
          <p className="mt-2 text-xs text-amber-800">
            🔒 {t('app.leads.distribution.gate.auto')}{' '}
            <Link to={`${ACTIVATION_PATHS.billing}?focus=plan`} className="font-medium underline">
              {t('app.leads.distribution.rules.upgrade')}
            </Link>
          </p>
        ) : null}

        <div className="mt-6">
          <h3 className="text-sm font-medium text-slate-800">
            {t('app.leads.distribution.rules_summary')}
          </h3>
          <ul className="mt-2 list-inside list-disc text-sm text-slate-600">
            {data.rules_summary_lines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>

        <div className="mt-6 rounded-xl bg-brand-50/80 px-4 py-3">
          <div className="text-xs font-medium uppercase text-brand-800">
            {t('app.leads.distribution.next')}
          </div>
          {data.next_preview ? (
            <div className="mt-1 text-lg font-semibold text-slate-900">{data.next_preview.display_name}</div>
          ) : (
            <div className="mt-1 text-sm text-amber-900">{t('app.leads.distribution.next_none')}</div>
          )}
          {data.next_preview?.subtitle ? <div className="text-xs text-slate-600">{data.next_preview.subtitle}</div> : null}
          {assignmentExplainLines.length > 0 ? (
            <ul className="mt-2 list-inside list-disc text-[11px] text-slate-600">
              {assignmentExplainLines.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : null}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            to={CRM_APP_PATHS.leadsDistributionRules}
            className="btn-secondary btn-sm inline-flex items-center gap-1"
          >
            {t('app.leads.distribution.edit_rules')}
            <IconChevronRight size={14} />
          </Link>
          <Link to={CRM_APP_PATHS.teamAvailability} className="btn-secondary btn-sm inline-flex items-center gap-1">
            {t('app.leads.distribution.team_load')}
            <IconArrowRight size={14} />
          </Link>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.leads.distribution.flow')}
        </h2>
        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm font-medium text-slate-700">
          {data.flow_steps.map((step, i) => (
            <span key={`${step}-${i}`} className="inline-flex items-center gap-2">
              {i > 0 ? <IconChevronRight size={16} className="text-slate-400" /> : null}
              <span className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">{step}</span>
            </span>
          ))}
        </div>
      </section>

      {data.next_preview && data.next_preview.reason_codes.length > 0 ? (
        <section className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-6 shadow-sm">
          <h2 className="text-sm font-semibold text-emerald-950">
            {t('app.leads.distribution.why_title')}
          </h2>
          <p className="mt-1 text-xs text-emerald-900/80">
            {t('app.leads.distribution.why_sub')}
          </p>
          <ul className="mt-3 space-y-1 text-sm text-emerald-950">
            {data.next_preview.reason_codes.map((c) => (
              <li key={c}>✔ {reasonLabel(c, t)}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.leads.distribution.team')}
        </h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.team.map((m) => (
            <div key={m.user_id} className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-slate-900">{m.display_name}</span>
                <span className="text-lg" aria-hidden>
                  {statusDot(m.status)}
                </span>
              </div>
              <div className="mt-2 text-xs text-slate-600">
                {m.status === 'available'
                  ? t('app.leads.distribution.status.available')
                  : m.status === 'busy'
                    ? t('app.leads.distribution.status.busy')
                    : t('app.leads.distribution.status.offline')}
              </div>
              <div className="mt-2 text-sm text-slate-800">
                {t('app.leads.distribution.load')}:{' '}
                <span className="font-semibold">{m.lead_load}</span> {t('app.leads.distribution.leads')}
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {t('app.leads.distribution.languages')}: {m.languages.join(', ') || '—'}
              </div>
              {m.working_hours_configured ? (
                <div className="mt-1 text-[11px] text-slate-600">
                  {m.within_working_hours
                    ? t('app.leads.distribution.wh.in_window')
                    : t('app.leads.distribution.wh.outside_window')}
                </div>
              ) : (
                <div className="mt-1 text-[11px] text-slate-400">
                  {t('app.leads.distribution.wh.not_configured')}
                </div>
              )}
            </div>
          ))}
        </div>
        {data.team.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">{t('app.leads.distribution.no_team')}</p>
        ) : null}
      </section>

      {data.alerts.length > 0 ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50/60 p-6">
          <h2 className="text-sm font-semibold text-amber-950">
            {t('app.leads.distribution.alerts')}
          </h2>
          <ul className="mt-2 space-y-1 text-sm text-amber-900">
            {data.alerts.map((a) => (
              <li key={a.code + a.message}>⚠ {a.message}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
        <div className="font-medium text-slate-800">
          {t('app.leads.distribution.upsell.smart')}
        </div>
        <div>
          {!data.feature_gate.advanced_rules_allowed ? (
            <span>
              🔒 {t('app.leads.distribution.upsell.team')}{' '}
              <Link to={`${ACTIVATION_PATHS.billing}?focus=plan`} className="text-brand-700 underline">
                {t('app.leads.distribution.rules.upgrade')}
              </Link>
            </span>
          ) : (
            <span>{t('app.leads.distribution.upsell.included')}</span>
          )}
        </div>
        <div className="mt-2">
          {!data.feature_gate.load_balance_pro ? (
            <span>
              {t('app.leads.distribution.upsell.balance')} — 🔒 Pro{' '}
              <Link to={`${ACTIVATION_PATHS.billing}?focus=plan`} className="text-brand-700 underline">
                {t('app.leads.distribution.rules.upgrade')}
              </Link>
            </span>
          ) : null}
        </div>
      </section>
    </div>
    </PageShell>
  )
}
