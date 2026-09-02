import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  createAutomationRule,
  deleteAutomationRule,
  listAutomationRules,
  patchAutomationRule,
  type AutomationRule,
} from '../api/automationRules'
import { listVacancies } from '../api/client'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader, Toolbar } from '../components/layout'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { useI18n } from '../i18n'
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../utils/friendlyError'

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

type LqNormOp = 'eq' | 'neq' | 'in' | 'exists' | 'not_exists'

const LQ_NORM_OPS: LqNormOp[] = ['eq', 'neq', 'in', 'exists', 'not_exists']

const defaultLqNormRow = (): { key: string; op: LqNormOp; value: string } => ({
  key: '',
  op: 'eq',
  value: '',
})

const TRIGGERS = [
  { value: 'candidate.created', label: 'candidate.created' },
  { value: 'candidate.stage_changed', label: 'candidate.stage_changed' },
  {
    value: 'candidate.risk_band',
    label: 'candidate.risk_band (hourly risk job)',
  },
  { value: 'document.expiring', label: 'document.expiring' },
  { value: 'lead.processed', label: 'lead.processed' },
  { value: 'lead.pipeline.stage_changed', label: 'lead.pipeline.stage_changed' },
  {
    value: 'lead.qualification',
    label: 'lead.qualification (ingest routing — §2.10)',
  },
] as const

export default function AutomationRulesPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [bannerError, setBannerError] = useState<FriendlyErrorInfo | null>(null)
  const [items, setItems] = useState<AutomationRule[]>([])

  const [newTrigger, setNewTrigger] = useState<(typeof TRIGGERS)[number]['value']>('candidate.stage_changed')
  const [newTitle, setNewTitle] = useState('Follow up')
  const [newDueMin, setNewDueMin] = useState(60)
  const [newStageTo, setNewStageTo] = useState('')
  const [newRiskBand, setNewRiskBand] = useState<'high' | 'critical'>('high')
  const [newPriority, setNewPriority] = useState(10)
  const [lqSource, setLqSource] = useState('meta')
  const [lqNormRows, setLqNormRows] = useState(() => [defaultLqNormRow()])
  const [lqVacancyId, setLqVacancyId] = useState('')
  const [lqRecruiterId, setLqRecruiterId] = useState('')
  const [lqNote, setLqNote] = useState('')
  const [vacancyOptions, setVacancyOptions] = useState<Array<{ id: string; title: string }>>([])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setBannerError(null)
    try {
      const res = await listAutomationRules()
      setItems(Array.isArray(res.items) ? res.items : [])
    } catch (err: any) {
      const fb = t('app.automation_rules.errors.load_failed')
      if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
        setBannerError(getFriendlyErrorInfo(err, fb, t))
      }
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [planLimitModal, t])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const res = await listVacancies({ limit: 300 })
        const raw: any[] = Array.isArray((res as any)?.items) ? (res as any).items : []
        if (!cancelled) {
          setVacancyOptions(
            raw
              .map((v) => ({
                id: String(v?.id || '').trim(),
                title: String(v?.title || v?.vacancy_title || '').trim() || '—',
              }))
              .filter((v) => v.id.length > 0),
          )
        }
      } catch {
        if (!cancelled) setVacancyOptions([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const handleCreate = useCallback(async () => {
    setLoading(true)
    setError(null)
    setBannerError(null)
    try {
      if (newTrigger === 'lead.qualification') {
        const vid = lqVacancyId.trim()
        if (!vid) {
          setError(t('app.automation_rules.errors.lq_vacancy_required'))
          return
        }
        const src = lqSource.trim().toLowerCase()
        const hasNorm = lqNormRows.some((r) => r.key.trim().length > 0)
        if (!src && !hasNorm) {
          setError(t('app.automation_rules.errors.lq_condition_required'))
          return
        }
        const recruiterTrim = lqRecruiterId.trim()
        if (recruiterTrim && !UUID_RE.test(recruiterTrim)) {
          setError(t('app.automation_rules.errors.lq_recruiter_uuid'))
          return
        }
        const conditions: Record<string, unknown> = {}
        if (src) conditions.source = src
        for (const row of lqNormRows) {
          const nk = row.key.trim()
          if (!nk) continue
          const path = `normalized.${nk}`
          if (row.op === 'eq') {
            conditions[path] = row.value
          } else if (row.op === 'neq') {
            conditions[path] = { op: 'neq', value: row.value }
          } else if (row.op === 'in') {
            const parts = row.value
              .split(/[,;]+/)
              .map((s) => s.trim())
              .filter(Boolean)
            if (parts.length === 0) {
              setError(t('app.automation_rules.errors.lq_in_values_required'))
              return
            }
            conditions[path] = { op: 'in', value: parts }
          } else if (row.op === 'exists') {
            conditions[path] = { op: 'exists' }
          } else if (row.op === 'not_exists') {
            conditions[path] = { op: 'not_exists' }
          }
        }
        await createAutomationRule({
          trigger: 'lead.qualification',
          priority: Math.max(0, Math.min(1_000_000, Number(newPriority) || 0)),
          title: newTitle.trim() || t('app.automation_rules.lq.default_title'),
          conditions,
          actions: {
            set_vacancy_id: vid,
            ...(recruiterTrim ? { set_recruiter_id: recruiterTrim } : {}),
            ...(lqNote.trim() ? { note: lqNote.trim() } : {}),
          },
        })
      } else {
        const conditions: Record<string, any> = {}
        if (newTrigger === 'candidate.stage_changed' && newStageTo.trim()) {
          conditions['stage_to'] = newStageTo.trim()
        }
        if (newTrigger === 'candidate.risk_band') {
          conditions['risk_band'] = newRiskBand
        }
        const dueMin =
          newTrigger === 'candidate.risk_band'
            ? Math.max(120, Number(newDueMin) || 0)
            : Math.max(0, Number(newDueMin) || 0)
        const actions = {
          create_reminder: {
            title: newTitle.trim() || 'Follow up',
            entity_type: newTrigger.startsWith('lead.') ? 'lead' : newTrigger.startsWith('candidate.') ? 'candidate' : 'custom',
            due_in_minutes: dueMin,
          },
        }
        await createAutomationRule({
          trigger: newTrigger,
          title: newTitle.trim() || null,
          conditions: Object.keys(conditions).length ? conditions : null,
          actions,
        })
      }
      await load()
    } catch (err: any) {
      const fb = t('app.automation_rules.errors.create_failed')
      if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
        setBannerError(getFriendlyErrorInfo(err, fb, t))
      }
    } finally {
      setLoading(false)
    }
  }, [
    load,
    planLimitModal,
    lqNormRows,
    lqNote,
    lqRecruiterId,
    lqSource,
    lqVacancyId,
    newDueMin,
    newPriority,
    newRiskBand,
    newStageTo,
    newTitle,
    newTrigger,
    t,
  ])

  const sorted = useMemo(
    () => [...items].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at))),
    [items],
  )

  const isLq = newTrigger === 'lead.qualification'

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          breadcrumbItems={[
            { label: t('app.automations.hub.title', { defaultValue: 'Automations' }), to: CRM_APP_PATHS.automations },
            { label: t('app.automation_rules.title') },
          ]}
          kind="action"
          primaryAction={
            <button type="button" className="btn-primary btn-sm" onClick={() => void handleCreate()} disabled={loading}>
              {loading ? t('common.loading') : t('common.actions.create')}
            </button>
          }
          secondaryActions={
            <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={loading}>
              {loading ? t('common.loading') : t('common.actions.refresh')}
            </button>
          }
        />
        <p className="mt-2 text-xs text-amber-800/90">{t('app.automation_rules.risk_band_hint')}</p>
        <p className="mt-1 text-xs text-slate-600">{t('app.automation_rules.lq.hint')}</p>
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pb-4">
      {bannerError ? (
        <ErrorRecoveryBanner
          info={bannerError}
          onRetry={() => {
            setBannerError(null)
            void load()
          }}
          retryLabel={t('common.actions.refresh')}
          {...friendlyErrorBannerSecondary(
            bannerError,
            CRM_APP_PATHS.settingsBilling,
            t('app.settings.billing.badge'),
          )}
        />
      ) : null}

      <section className="card p-4 space-y-3">
        <div className="text-sm font-semibold">{t('app.automation_rules.create')}</div>
        {error ? <div className="text-sm text-rose-600">{String(error)}</div> : null}
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
          <label className="text-sm">
            <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.fields.trigger')}</div>
            <select className="input w-full" value={newTrigger} onChange={(e) => setNewTrigger(e.target.value as any)}>
              {TRIGGERS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.fields.title')}</div>
            <input className="input w-full" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
          </label>
          {!isLq ? (
            <label className="text-sm">
              <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.fields.due_in')}</div>
              <input className="input w-full" type="number" min={0} value={newDueMin} onChange={(e) => setNewDueMin(Number(e.target.value) || 0)} />
            </label>
          ) : (
            <label className="text-sm">
              <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.fields.priority')}</div>
              <input className="input w-full" type="number" min={0} max={1000000} value={newPriority} onChange={(e) => setNewPriority(Number(e.target.value) || 0)} />
            </label>
          )}
          {!isLq ? (
            <label className="text-sm">
              <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.fields.stage_to')}</div>
              <input
                className="input w-full"
                value={newStageTo}
                onChange={(e) => setNewStageTo(e.target.value)}
                placeholder={t('app.automation_rules.fields.stage_to_placeholder')}
                disabled={newTrigger !== 'candidate.stage_changed'}
              />
            </label>
          ) : (
            <label className="text-sm">
              <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.lq.source')}</div>
              <input className="input w-full" value={lqSource} onChange={(e) => setLqSource(e.target.value)} placeholder="meta" />
            </label>
          )}
          {!isLq ? (
            <label className="text-sm">
              <div className="mb-1 text-xs text-slate-600">
                {t('app.automation_rules.fields.risk_band')}
              </div>
              <select
                className="input w-full"
                value={newRiskBand}
                onChange={(e) => setNewRiskBand(e.target.value as 'high' | 'critical')}
                disabled={newTrigger !== 'candidate.risk_band'}
              >
                <option value="high">high</option>
                <option value="critical">critical</option>
              </select>
            </label>
          ) : (
            <label className="text-sm md:col-span-2">
              <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.lq.vacancy')}</div>
              <select className="input w-full" value={lqVacancyId} onChange={(e) => setLqVacancyId(e.target.value)}>
                <option value="">{t('app.automation_rules.lq.vacancy_placeholder')}</option>
                {vacancyOptions.map((v) => (
                  <option key={v.id} value={v.id}>{v.title}</option>
                ))}
              </select>
            </label>
          )}
        </div>
        {isLq ? (
          <div className="space-y-3">
            <div className="text-xs font-medium text-slate-600">{t('app.automation_rules.lq.norm_block_title')}</div>
            {lqNormRows.map((row, idx) => (
              <div
                key={idx}
                className="grid gap-3 md:grid-cols-12 md:items-end rounded-lg border border-slate-100 bg-slate-50/80 p-3"
              >
                <label className="text-sm md:col-span-3">
                  <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.lq.norm_key')}</div>
                  <input
                    className="input w-full"
                    value={row.key}
                    onChange={(e) => {
                      const v = e.target.value
                      setLqNormRows((prev) => prev.map((r, i) => (i === idx ? { ...r, key: v } : r)))
                    }}
                    placeholder="country"
                  />
                </label>
                <label className="text-sm md:col-span-3">
                  <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.lq.norm_op')}</div>
                  <select
                    className="input w-full"
                    value={row.op}
                    onChange={(e) => {
                      const op = e.target.value as LqNormOp
                      setLqNormRows((prev) => prev.map((r, i) => (i === idx ? { ...r, op } : r)))
                    }}
                  >
                    {LQ_NORM_OPS.map((op) => (
                      <option key={op} value={op}>
                        {t(`app.automation_rules.lq.ops.${op}`)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm md:col-span-5">
                  <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.lq.norm_value')}</div>
                  <input
                    className="input w-full"
                    value={row.value}
                    disabled={row.op === 'exists' || row.op === 'not_exists'}
                    onChange={(e) => {
                      const v = e.target.value
                      setLqNormRows((prev) => prev.map((r, i) => (i === idx ? { ...r, value: v } : r)))
                    }}
                    placeholder={
                      row.op === 'in'
                        ? t('app.automation_rules.lq.norm_value_placeholder_in')
                        : t('app.automation_rules.lq.norm_value_placeholder')
                    }
                  />
                </label>
                <div className="flex gap-2 md:col-span-1 md:justify-end">
                  {lqNormRows.length > 1 ? (
                    <button
                      type="button"
                      className="btn-secondary btn-xs whitespace-nowrap"
                      onClick={() => setLqNormRows((prev) => prev.filter((_, i) => i !== idx))}
                    >
                      {t('app.automation_rules.lq.remove_row')}
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
            {lqNormRows.length < 8 ? (
              <button
                type="button"
                className="btn-secondary btn-xs"
                onClick={() => setLqNormRows((prev) => [...prev, defaultLqNormRow()])}
              >
                {t('app.automation_rules.lq.add_row')}
              </button>
            ) : null}
            <label className="text-sm md:col-span-2 block">
              <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.lq.recruiter')}</div>
              <input
                className="input w-full font-mono text-xs"
                value={lqRecruiterId}
                onChange={(e) => setLqRecruiterId(e.target.value)}
                placeholder={t('app.automation_rules.lq.recruiter_placeholder')}
              />
            </label>
            <label className="text-sm block max-w-2xl">
              <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.lq.note')}</div>
              <input className="input w-full" value={lqNote} onChange={(e) => setLqNote(e.target.value)} />
            </label>
          </div>
        ) : null}
      </section>

      <section className="card p-4 space-y-3">
        <div className="text-sm font-semibold">{t('app.automation_rules.list')}</div>
        {sorted.length === 0 ? (
          <div className="text-sm text-slate-500">{t('app.automation_rules.empty')}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500 border-b border-slate-200">
                  <th className="py-2 pr-3">{t('app.automation_rules.columns.enabled')}</th>
                  <th className="py-2 pr-3">{t('app.automation_rules.columns.priority')}</th>
                  <th className="py-2 pr-3">{t('app.automation_rules.columns.trigger')}</th>
                  <th className="py-2 pr-3">{t('app.automation_rules.columns.title')}</th>
                  <th className="py-2 pr-3">{t('app.automation_rules.columns.conditions')}</th>
                  <th className="py-2 pr-3">{t('app.automation_rules.columns.actions')}</th>
                  <th className="py-2 text-right">{t('common.actions.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-2 pr-3">
                      <input
                        type="checkbox"
                        checked={!!r.enabled}
                        onChange={() => void patchAutomationRule(r.id, { enabled: !r.enabled }).then(load)}
                      />
                    </td>
                    <td className="py-2 pr-3 tabular-nums text-xs">{r.priority ?? 0}</td>
                    <td className="py-2 pr-3 font-mono text-xs">{r.trigger}</td>
                    <td className="py-2 pr-3">{r.title || '—'}</td>
                    <td className="py-2 pr-3">
                      <pre className="max-w-md whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(r.conditions || {}, null, 2)}</pre>
                    </td>
                    <td className="py-2 pr-3">
                      <pre className="max-w-md whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(r.actions || {}, null, 2)}</pre>
                    </td>
                    <td className="py-2 text-right">
                      <button
                        type="button"
                        className="btn-secondary btn-xs"
                        onClick={() => void deleteAutomationRule(r.id).then(load)}
                      >
                        {t('common.actions.delete')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      </div>
    </PageShell>
  )
}
