import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { funnelHasReadyForHandoff, getFunnel, listFunnels, type Funnel } from '../../api/funnels'
import { isHandoffEnabledForCompany, listTenantLinks } from '../../api/tenantLinks'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useCurrentTenantId } from '../../contexts/CurrentTenant'
import { useI18n } from '../../i18n'
import { useAuth } from '../../store/useAuth'

interface FunnelSelectorProps {
  companyId: string | null | undefined
  value: string | null | undefined
  onChange: (funnelId: string | null) => void
  disabled?: boolean
  moduleKey?: string
  funnelType?: 'candidate' | 'lead' | 'deal' | 'employee'
  hint?: string
  /** Vacancy assignment: tenant module catalog, not per-client copies. */
  catalog?: boolean
}

export default function FunnelSelector({
  companyId,
  value,
  onChange,
  disabled = false,
  moduleKey = 'recruitment',
  funnelType = 'candidate',
  hint,
  catalog = false,
}: FunnelSelectorProps) {
  const { t } = useI18n()
  const { me } = useAuth()
  const currentTenantId = useCurrentTenantId()
  const tenantId = (currentTenantId ?? (me as { tenant_id?: string } | null)?.tenant_id ?? '').trim()
  const [funnels, setFunnels] = useState<Funnel[]>([])
  const [loading, setLoading] = useState(true)
  const [handoffEnabled, setHandoffEnabled] = useState(false)

  const scopeCompanyId = String(companyId || '').trim()
  const requireHandoffReady = funnelType === 'candidate' && moduleKey === 'recruitment' && handoffEnabled

  const load = useCallback(async () => {
    if (!catalog && !scopeCompanyId) {
      setFunnels([])
      setHandoffEnabled(false)
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const [list, links] = await Promise.all([
        listFunnels({
          ...(catalog ? {} : { companyId: scopeCompanyId }),
          type: funnelType,
          moduleKey,
        }),
        tenantId && scopeCompanyId ? listTenantLinks(tenantId).catch(() => []) : Promise.resolve([]),
      ])
      let next = list
      const selectedId = String(value || '').trim()
      if (selectedId && !next.some((funnel) => funnel.id === selectedId)) {
        try {
          const current = await getFunnel(selectedId)
          next = [...next, current]
        } catch {
          /* keep catalog list */
        }
      }
      setFunnels(next)
      setHandoffEnabled(
        Boolean(scopeCompanyId && isHandoffEnabledForCompany(links, scopeCompanyId)),
      )
    } catch {
      setFunnels([])
      setHandoffEnabled(false)
    } finally {
      setLoading(false)
    }
  }, [catalog, scopeCompanyId, moduleKey, funnelType, tenantId, value])

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

  if (!catalog && !scopeCompanyId) {
    return (
      <p className="text-sm text-slate-500">
        {t('admin.candidate_profiles_page.funnel.need_company')}
      </p>
    )
  }

  if (loading) {
    return <div className="text-sm text-slate-500">{t('admin.candidate_profiles_page.funnel.loading')}</div>
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          {t('admin.candidate_profiles_page.funnel.label')}
        </label>
        <select
          value={value || ''}
          onChange={(e) => onChange(e.target.value || null)}
          disabled={disabled}
          className="input w-full max-w-md"
        >
          <option value="">{t('admin.candidate_profiles_page.funnel.none')}</option>
          {selectableFunnels.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
              {f.is_default ? ' ★' : ''}
            </option>
          ))}
          {selectedBlocked && selectedFunnel ? (
            <option value={selectedFunnel.id} disabled>
              {t('admin.candidate_profiles_page.funnel.missing_handoff_stage', {
                values: { name: selectedFunnel.name },
              })}
            </option>
          ) : null}
        </select>
        <p className="mt-1 text-xs text-slate-500">
          {requireHandoffReady
            ? t('admin.candidate_profiles_page.funnel.handoff_only')
            : (hint ?? t('admin.candidate_profiles_page.funnel.hint'))}{' '}
          <Link to={CRM_APP_PATHS.settingsFunnels} className="text-brand-600 hover:underline">
            {t('admin.candidate_profiles_page.funnel.edit_link')}
          </Link>
        </p>
        {selectedBlocked ? (
          <p className="mt-1 text-xs text-rose-700">
            {t('admin.candidate_profiles_page.funnel.blocked')}
          </p>
        ) : null}
      </div>
      {selectedFunnel && selectedFunnel.stages && selectedFunnel.stages.length > 0 && (
        <div>
          <div className="text-sm font-medium text-slate-700 mb-2">
            {t('admin.candidate_profiles_page.funnel.stages')}
          </div>
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
