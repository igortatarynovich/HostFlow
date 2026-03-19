import { useEffect, useMemo, useState } from 'react'
import { useI18n } from '../i18n'
import { useTenantInfo } from '../contexts/TenantInfo'
import { getOnboardingStatus } from '../api/client'

export function useBusinessTerminology() {
  const { t } = useI18n()
  const tenant = useTenantInfo()

  const [businessType, setBusinessType] = useState<'agency' | 'employer' | 'services' | null>(null)

  useEffect(() => {
    let mounted = true
    getOnboardingStatus()
      .then((status) => {
        const raw = String((status as any)?.business_type || '').trim().toLowerCase()
        if (!mounted) return
        if (raw === 'agency' || raw === 'employer' || raw === 'services') setBusinessType(raw)
        else setBusinessType(null)
      })
      .catch(() => {
        if (mounted) setBusinessType(null)
      })
    return () => {
      mounted = false
    }
  }, [])

  const isEmployerTenant = businessType
    ? businessType === 'employer'
    : String(tenant?.type || '').trim().toLowerCase() === 'company'
  const isServicesTenant = businessType === 'services'
  const effectiveBusinessType: 'agency' | 'employer' | 'services' = businessType
    ? businessType
    : (isEmployerTenant ? 'employer' : 'agency')

  return useMemo(() => {
    const entityPlural = isEmployerTenant || isServicesTenant
      ? t('app.dashboard.terms.companies_plural', { defaultValue: 'Companies' })
      : t('app.dashboard.terms.clients_plural', { defaultValue: 'Clients' })
    const entitySingular = isEmployerTenant || isServicesTenant
      ? t('app.dashboard.terms.companies_singular', { defaultValue: 'Company' })
      : t('app.dashboard.terms.clients_singular', { defaultValue: 'Client' })
    const openEntityLabel = isEmployerTenant || isServicesTenant
      ? t('common.actions.open_companies', { defaultValue: 'Open companies' })
      : t('common.actions.open_clients', { defaultValue: 'Open clients' })

    return {
      businessType: effectiveBusinessType,
      isEmployerTenant,
      isServicesTenant,
      entityPlural,
      entitySingular,
      openEntityLabel,
    }
  }, [effectiveBusinessType, isEmployerTenant, isServicesTenant, t])
}
