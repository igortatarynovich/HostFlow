import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { createAutomationRule, deleteAutomationRule, listAutomationRules, patchAutomationRule, type AutomationRule } from '../api/automationRules'
import { useI18n } from '../i18n'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

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
] as const

export default function AutomationRulesPage() {
  const { t } = useI18n()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [items, setItems] = useState<AutomationRule[]>([])

  const [newTrigger, setNewTrigger] = useState<(typeof TRIGGERS)[number]['value']>('candidate.stage_changed')
  const [newTitle, setNewTitle] = useState('Follow up')
  const [newDueMin, setNewDueMin] = useState(60)
  const [newStageTo, setNewStageTo] = useState('')
  const [newRiskBand, setNewRiskBand] = useState<'high' | 'critical'>('high')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listAutomationRules()
      setItems(Array.isArray(res.items) ? res.items : [])
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err?.message ?? 'Failed to load rules')
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleCreate = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
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
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? err?.message ?? 'Failed to create rule')
    } finally {
      setLoading(false)
    }
  }, [load, newDueMin, newRiskBand, newStageTo, newTitle, newTrigger])

  const sorted = useMemo(() => [...items].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at))), [items])

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col space-y-0 gap-0">
      <header className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <Link to={CRM_APP_PATHS.automations} className="text-sm font-medium text-brand-600 hover:text-brand-800 hover:underline">
          {t('app.automations.hub.back')}
        </Link>
        <h1 className="mt-2 text-xl font-semibold text-slate-900">
          {t('app.automation_rules.title')}
        </h1>
        <p className="text-xs text-slate-500">
          {t('app.automation_rules.subtitle')}
        </p>
        <p className="mt-2 text-xs text-amber-800/90">
          {t('app.automation_rules.risk_band_hint')}
        </p>
      </header>

      <section className="card p-4 space-y-3">
        <div className="text-sm font-semibold">{t('app.automation_rules.create')}</div>
        {error ? <div className="text-sm text-red-600">{String(error)}</div> : null}
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
          <label className="text-sm">
            <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.fields.due_in')}</div>
            <input className="input w-full" type="number" min={0} value={newDueMin} onChange={(e) => setNewDueMin(Number(e.target.value) || 0)} />
          </label>
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
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn-primary btn-sm" onClick={() => void handleCreate()} disabled={loading}>
            {loading ? t('common.loading') : t('common.actions.create')}
          </button>
          <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={loading}>
            {t('common.actions.refresh')}
          </button>
        </div>
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
  )
}
