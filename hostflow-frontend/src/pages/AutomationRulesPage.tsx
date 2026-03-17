import { useCallback, useEffect, useMemo, useState } from 'react'
import { createAutomationRule, deleteAutomationRule, listAutomationRules, patchAutomationRule, type AutomationRule } from '../api/automationRules'
import { useI18n } from '../i18n'

const TRIGGERS = [
  { value: 'candidate.created', label: 'candidate.created' },
  { value: 'candidate.stage_changed', label: 'candidate.stage_changed' },
  { value: 'document.expiring', label: 'document.expiring' },
  { value: 'lead.processed', label: 'lead.processed' },
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
      const actions = {
        create_reminder: {
          title: newTitle.trim() || 'Follow up',
          entity_type: newTrigger.startsWith('lead.') ? 'lead' : newTrigger.startsWith('candidate.') ? 'candidate' : 'custom',
          due_in_minutes: Math.max(0, Number(newDueMin) || 0),
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
  }, [load, newDueMin, newStageTo, newTitle, newTrigger])

  const sorted = useMemo(() => [...items].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at))), [items])

  return (
    <div className="space-y-4">
      <header className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">
          {t('app.automation_rules.title', { defaultValue: 'Automation rules (minimal builder)' })}
        </h1>
        <p className="text-xs text-slate-500">
          {t('app.automation_rules.subtitle', { defaultValue: 'Define simple triggers → create reminder actions.' })}
        </p>
      </header>

      <section className="card p-4 space-y-3">
        <div className="text-sm font-semibold">{t('app.automation_rules.create', { defaultValue: 'Create rule' })}</div>
        {error ? <div className="text-sm text-red-600">{String(error)}</div> : null}
        <div className="grid gap-3 md:grid-cols-4">
          <label className="text-sm">
            <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.fields.trigger', { defaultValue: 'Trigger' })}</div>
            <select className="input w-full" value={newTrigger} onChange={(e) => setNewTrigger(e.target.value as any)}>
              {TRIGGERS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.fields.title', { defaultValue: 'Reminder title' })}</div>
            <input className="input w-full" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
          </label>
          <label className="text-sm">
            <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.fields.due_in', { defaultValue: 'Due in (minutes)' })}</div>
            <input className="input w-full" type="number" min={0} value={newDueMin} onChange={(e) => setNewDueMin(Number(e.target.value) || 0)} />
          </label>
          <label className="text-sm">
            <div className="mb-1 text-xs text-slate-600">{t('app.automation_rules.fields.stage_to', { defaultValue: 'Stage to (optional)' })}</div>
            <input className="input w-full" value={newStageTo} onChange={(e) => setNewStageTo(e.target.value)} placeholder="contacted" />
          </label>
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn-primary btn-sm" onClick={() => void handleCreate()} disabled={loading}>
            {loading ? t('common.loading', { defaultValue: 'Loading…' }) : t('common.actions.create', { defaultValue: 'Create' })}
          </button>
          <button type="button" className="btn-secondary btn-sm" onClick={() => void load()} disabled={loading}>
            {t('common.actions.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
      </section>

      <section className="card p-4 space-y-3">
        <div className="text-sm font-semibold">{t('app.automation_rules.list', { defaultValue: 'Rules' })}</div>
        {sorted.length === 0 ? (
          <div className="text-sm text-slate-500">{t('app.automation_rules.empty', { defaultValue: 'No rules yet.' })}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500 border-b border-slate-200">
                  <th className="py-2 pr-3">{t('app.automation_rules.columns.enabled', { defaultValue: 'On' })}</th>
                  <th className="py-2 pr-3">{t('app.automation_rules.columns.trigger', { defaultValue: 'Trigger' })}</th>
                  <th className="py-2 pr-3">{t('app.automation_rules.columns.title', { defaultValue: 'Title' })}</th>
                  <th className="py-2 pr-3">{t('app.automation_rules.columns.conditions', { defaultValue: 'Conditions' })}</th>
                  <th className="py-2 pr-3">{t('app.automation_rules.columns.actions', { defaultValue: 'Actions' })}</th>
                  <th className="py-2 text-right">{t('common.actions.actions', { defaultValue: 'Actions' })}</th>
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
                        {t('common.actions.delete', { defaultValue: 'Delete' })}
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

