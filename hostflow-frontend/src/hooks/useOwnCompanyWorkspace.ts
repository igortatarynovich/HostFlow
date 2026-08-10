import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createOwnCompany, listOwnCompanies, ownCompanySettings, setActiveOwnCompany } from '../api/client'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { useToast } from '../components/Toast'
import { useTeamOverviewNav } from '../contexts/TeamOverviewNavContext'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { canUseTeamOverviewLane } from '../auth/trustRoles'
import { usePermissions } from './usePermissions'

export function canCreateOwnCompanyRole(
  role: string | null | undefined,
  presetId?: string | null,
): boolean {
  return canUseTeamOverviewLane({ role, presetId })
}

function effectiveOwnCompanyLimit(maxCompanies: number | null | undefined): number | null {
  if (maxCompanies == null) return null
  if (maxCompanies <= 0) return 1
  return maxCompanies
}

export function useOwnCompanyWorkspace() {
  const { me } = useAuth()
  const navigate = useNavigate()
  const { can, isClientTenant, rawRole, presetId } = usePermissions()
  const { t } = useI18n()
  const { notify } = useToast()
  const { teamOverview } = useTeamOverviewNav()

  const [ownCompanies, setOwnCompanies] = useState<Array<{ id: string; name: string }>>([])
  const [activeOwnCompanyId, setActiveOwnCompanyId] = useState<string | null>(() => ownCompanySettings.get())
  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [createBusy, setCreateBusy] = useState(false)

  const canAddOwnCompany =
    canCreateOwnCompanyRole(rawRole || me?.role, presetId) && !isClientTenant && Boolean(me?.tenant_id)
  const ownCompanyLimit = effectiveOwnCompanyLimit(teamOverview?.license?.max_companies)
  const atPlanLimit =
    ownCompanyLimit != null && ownCompanies.length >= ownCompanyLimit && teamOverview?.license != null

  useEffect(() => {
    let cancelled = false
    if (!me?.tenant_id) return
    ;(async () => {
      try {
        const res = await listOwnCompanies()
        const items = Array.isArray((res as any)?.items) ? (res as any).items : []
        if (cancelled) return
        setOwnCompanies(items.map((x: any) => ({ id: String(x.id), name: String(x.name || x.id) })))
        const active = String((res as any)?.active_own_company_id || '').trim() || ownCompanySettings.get()
        if (active) {
          setActiveOwnCompanyId(active)
          ownCompanySettings.set(active)
        } else if (items.length > 0) {
          setActiveOwnCompanyId(String(items[0].id))
          ownCompanySettings.set(String(items[0].id))
        }
      } catch {
        if (!cancelled) setOwnCompanies([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [me?.tenant_id])

  const selectCompany = useCallback((next: string) => {
    setActiveOwnCompanyId(next)
    ownCompanySettings.set(next)
    void setActiveOwnCompany(next).catch(() => {})
  }, [])

  const submitCreate = useCallback(async () => {
    const trimmed = newName.trim()
    if (!trimmed || createBusy) return
    setCreateBusy(true)
    try {
      const created = await createOwnCompany({ name: trimmed })
      const newId = String(created.id)
      await setActiveOwnCompany(newId)
      ownCompanySettings.set(newId)
      setActiveOwnCompanyId(newId)
      const res = await listOwnCompanies()
      const items = Array.isArray((res as any)?.items) ? (res as any).items : []
      setOwnCompanies(items.map((x: any) => ({ id: String(x.id), name: String(x.name || x.id) })))
      notify({ title: t('app.topbar.own_company_create_success'), variant: 'success' })
      setCreateOpen(false)
      setNewName('')
    } catch (e: any) {
      const status = e?.response?.status
      if (status === 402) {
        notify({
          title: t('app.topbar.own_company_plan_limit_402'),
          description: t('app.topbar.own_company_upgrade_hint'),
          variant: 'error',
        })
      } else {
        notify({
          title: t('app.topbar.own_company_create_error'),
          description: typeof e?.message === 'string' ? e.message : undefined,
          variant: 'error',
        })
      }
    } finally {
      setCreateBusy(false)
    }
  }, [createBusy, newName, notify, t])

  const openBilling = useCallback(() => {
    setCreateOpen(false)
    navigate(CRM_APP_PATHS.settingsBilling)
  }, [navigate])

  const visible = ownCompanies.length > 0 || canAddOwnCompany

  return {
    visible,
    ownCompanies,
    activeOwnCompanyId,
    selectCompany,
    canAddOwnCompany,
    atPlanLimit,
    createOpen,
    setCreateOpen,
    newName,
    setNewName,
    createBusy,
    submitCreate,
    openBilling,
    canOpenBilling: can('admin.users'),
  }
}
