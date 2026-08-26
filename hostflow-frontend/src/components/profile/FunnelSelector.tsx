import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { funnelHasReadyForHandoff, listFunnels, type Funnel } from '../../api/funnels'
import { isHandoffEnabledForCompany, listTenantLinks } from '../../api/tenantLinks'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useCurrentTenantId } from '../../contexts/CurrentTenant'
import { useAuth } from '../../store/useAuth'

interface FunnelSelectorProps {
  companyId: string | null | undefined
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
  const { me } = useAuth()
  const currentTenantId = useCurrentTenantId()
  const tenantId = (currentTenantId ?? (me as { tenant_id?: string } | null)?.tenant_id ?? '').trim()
  const [funnels, setFunnels] = useState<Funnel[]>([])
  const [loading, setLoading] = useState(true)
  const [handoffEnabled, setHandoffEnabled] = useState(false)

  const scopeCompanyId = String(companyId || '').trim()
  const requireHandoffReady = funnelType === 'candidate' && moduleKey === 'recruitment' && handoffEnabled

  const load = useCallback(async () => {
    if (!scopeCompanyId) {
      setFunnels([])
      setHandoffEnabled(false)
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const [list, links] = await Promise.all([
        listFunnels({
          companyId: scopeCompanyId,
          type: funnelType,
          moduleKey,
        }),
        tenantId ? listTenantLinks(tenantId).catch(() => []) : Promise.resolve([]),
      ])
      setFunnels(list)
      setHandoffEnabled(isHandoffEnabledForCompany(links, scopeCompanyId))
    } catch {
      setFunnels([])
      setHandoffEnabled(false)
    } finally {
      setLoading(false)
    }
  }, [scopeCompanyId, moduleKey, funnelType, tenantId])

  useEffect(() => {
    void load()
  }, [load])

  const selectableFunnels = useMemo(() => {
    if (!requireHandoffReady) return funnels
    return funnels.filter((funnel) => funnelHasReadyForHandoff(funnel))
  }, [funnels, requireHandoffReady])

  const selectedFunnel = funnels.find((f) => f.id === value)
  const selectedBlocked = Boolean(
    requireHandoffReady && value && selectedFunnel && !funnelHasReadyForHandoff(selectedFunnel),
  )

  if (!scopeCompanyId) {
    return (
      <p className="text-sm text-slate-500">
        Выберите компанию (client), чтобы привязать company-scoped воронку.
      </p>
    )
  }

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
          {selectableFunnels.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
              {f.is_default ? ' ★' : ''}
            </option>
          ))}
          {selectedBlocked && selectedFunnel ? (
            <option value={selectedFunnel.id} disabled>
              {selectedFunnel.name} (нет этапа «Готов к передаче»)
            </option>
          ) : null}
        </select>
        <p className="mt-1 text-xs text-slate-500">
          {requireHandoffReady
            ? 'У клиента включён handoff: доступны только воронки с этапом «Готов к передаче».'
            : (hint ?? 'Этапы берутся из company-scoped воронок.')}{' '}
          <Link to={CRM_APP_PATHS.settingsFunnels} className="text-brand-600 hover:underline">
            Редактировать воронки
          </Link>
        </p>
        {selectedBlocked ? (
          <p className="mt-1 text-xs text-rose-700">
            Эта воронка не подходит для handoff: добавьте этап «Готов к передаче» или выберите другую.
          </p>
        ) : null}
      </div>
      {selectedFunnel && selectedFunnel.stages && selectedFunnel.stages.length > 0 && (
        <div>
          <div className="text-sm font-medium text-slate-700 mb-2">Этапы выбранной воронки</div>
          <div className="flex flex-wrap gap-2">
            {selectedFunnel.stages.map((s) => (
              <span
                key={s.id}
                className="inline-flex rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700"
              >
                {s.label} <span className="text-slate-500 font-mono">({s.code})</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
