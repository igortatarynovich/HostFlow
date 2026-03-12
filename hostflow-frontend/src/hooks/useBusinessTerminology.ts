import { useMemo } from 'react'
import { useI18n } from '../i18n'
import { useTenantInfo } from '../contexts/TenantInfo'

export function useBusinessTerminology() {
  const { t } = useI18n()
  const tenant = useTenantInfo()

  const isEmployerTenant = String(tenant?.type || '').trim().toLowerCase() === 'company'

  return useMemo(() => {
    const entityPlural = isEmployerTenant
      ? t('app.dashboard.terms.companies_plural', { defaultValue: 'Companies' })
      : t('app.dashboard.terms.clients_plural', { defaultValue: 'Clients' })
    const entitySingular = isEmployerTenant
      ? t('app.dashboard.terms.companies_singular', { defaultValue: 'Company' })
      : t('app.dashboard.terms.clients_singular', { defaultValue: 'Client' })
    const openEntityLabel = isEmployerTenant
      ? t('common.actions.open_companies', { defaultValue: 'Open companies' })
      : t('common.actions.open_clients', { defaultValue: 'Open clients' })

    return {
      isEmployerTenant,
      entityPlural,
      entitySingular,
      openEntityLabel,
    }
  }, [isEmployerTenant, t])
}
