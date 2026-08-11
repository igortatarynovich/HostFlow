import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listFunnels, type Funnel } from '../../api/funnels'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'

interface FunnelSelectorProps {
  /** Optional legacy filter; omit for tenant-wide catalog (Vacancy assignment SoT). */
  companyId?: string | null | undefined
  value: string | null | undefined
  onChange: (funnelId: string | null) => void
  disabled?: boolean
  moduleKey?: string
  funnelType?: 'candidate' | 'lead' | 'deal' | 'employee'
  hint?: string
}

export default function FunnelSelector({
  companyId,
  value,
  onChange,
  disabled = false,
  moduleKey = 'recruitment',
  funnelType = 'candidate',
  hint,
}: FunnelSelectorProps) {
  const { t } = useI18n()
  const [funnels, setFunnels] = useState<Funnel[]>([])
  const [loading, setLoading] = useState(true)

  const scopeCompanyId = String(companyId || '').trim()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const list = await listFunnels({
        // Vacancy SoT: show tenant catalog; companyId only narrows if explicitly needed elsewhere.
        companyId: funnelType === 'candidate' || funnelType === 'lead' ? undefined : scopeCompanyId || undefined,
        type: funnelType,
        moduleKey,
      })
      setFunnels(list)
    } catch {
      setFunnels([])
    } finally {
      setLoading(false)
    }
  }, [scopeCompanyId, moduleKey, funnelType])

  useEffect(() => {
    void load()
  }, [load])

  const selectedFunnel = funnels.find((f) => f.id === value)

  if (loading) {
    return <div className="text-sm text-slate-500">Загрузка воронок…</div>
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Воронка (этапы)</label>
        <select
          value={value || ''}
          onChange={(e) => onChange(e.target.value || null)}
          disabled={disabled}
          className="input w-full max-w-md"
        >
          <option value="">— не выбрана —</option>
          {funnels.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
              {f.is_default ? ' ★' : ''}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-slate-500">
          {hint ??
            t('app.profiles.funnel_selector.hint', {
              defaultValue: 'Pipeline is assigned on the vacancy.',
            })}{' '}
          <Link to={CRM_APP_PATHS.settingsFunnels} className="text-brand-600 hover:underline">
            {t('app.profiles.funnel_selector.edit_funnels', { defaultValue: 'Edit funnels' })}
          </Link>
        </p>
      </div>
      {selectedFunnel && selectedFunnel.stages && selectedFunnel.stages.length > 0 ? (
        <div>
          <div className="text-sm font-medium text-slate-700 mb-2">Этапы выбранной воронки</div>
          <div className="flex flex-wrap gap-2">
            {selectedFunnel.stages.map((s) => (
              <span
                key={s.id}
                className="inline-flex rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700"
              >
                {s.label} <span className="font-mono text-slate-500">({s.code})</span>
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
