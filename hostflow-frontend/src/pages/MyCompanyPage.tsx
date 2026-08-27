/**
 * Own-company profile (legal entity / brand the tenant operates from).
 *
 * Scope: company profile only — overview, requisites, bank, contacts, etc.
 * Tenant organization hub (subscription, users, modules, manage companies list)
 * is intentionally OUT OF SCOPE here — planned as a separate screen later.
 */
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  getOnboardingStatus,
  listOwnCompanies,
  ownCompanySettings,
  setActiveOwnCompany,
  type OwnCompanyRecord,
} from '../api/client'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { PageShell, PageShellHeader } from '../components/layout'
import { OwnCompanyProfileView } from '../components/my-company/OwnCompanyProfileView'
import {
  OWN_COMPANY_PROFILE_TABS,
  parseOwnCompanyProfileTab,
  type OwnCompanyProfileTab,
} from '../components/my-company/ownCompanyProfileUtils'
import { PageHeader } from '../components/nav/PageHeader'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { useI18n } from '../i18n'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'

export default function MyCompanyPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const planLimitModal = usePlanLimitModal()

  const [ownCompanies, setOwnCompanies] = useState<OwnCompanyRecord[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [stats, setStats] = useState<{
    employees: number | null
    vacancies: number | null
    clients: number | null
    orders: number | null
  }>({ employees: null, vacancies: null, clients: null, orders: null })

  const tab = parseOwnCompanyProfileTab(searchParams.get('tab'))

  useEffect(() => {
    let mounted = true
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const [ownRes, onboarding] = await Promise.all([
          listOwnCompanies(),
          getOnboardingStatus().catch(() => null),
        ])
        if (!mounted) return
        const items = Array.isArray(ownRes?.items) ? ownRes.items.filter((c) => !c.is_archived) : []
        setOwnCompanies(items)
        const preferred =
          String(ownRes?.active_own_company_id || '').trim() ||
          ownCompanySettings.get() ||
          items[0]?.id ||
          null
        setActiveId(preferred)
        if (preferred) {
          try {
            ownCompanySettings.set(preferred)
          } catch {
            // ignore
          }
        }
        setStats({
          employees: null,
          vacancies: onboarding?.vacancies_count ?? null,
          clients: onboarding?.clients_count ?? null,
          orders: onboarding?.service_orders_count ?? null,
        })
      } catch (err: any) {
        if (!mounted) return
        const fb = t('app.my_company.errors.load_failed', { defaultValue: 'Failed to load company profiles' })
        if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
          setError(getFriendlyErrorInfo(err, fb, t))
        }
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [planLimitModal, t])

  const company = useMemo(() => {
    if (!ownCompanies.length) return null
    return ownCompanies.find((item) => item.id === activeId) || ownCompanies[0]
  }, [activeId, ownCompanies])

  const setTab = (next: OwnCompanyProfileTab) => {
    const params = new URLSearchParams(searchParams)
    if (next === 'overview') params.delete('tab')
    else params.set('tab', next)
    setSearchParams(params, { replace: true })
  }

  const selectCompany = async (id: string) => {
    setActiveId(id)
    try {
      ownCompanySettings.set(id)
      await setActiveOwnCompany(id)
    } catch {
      // best-effort active switch
    }
  }

  const openEditor = () => {
    if (!company) return
    const sectionByTab: Partial<Record<OwnCompanyProfileTab, string>> = {
      requisites: 'legal',
      bank: 'bank_accounts',
      contacts: 'contacts',
      overview: 'legal',
    }
    const section = sectionByTab[tab]
    const qs = section ? `?section=${section}` : ''
    navigate(`${CRM_APP_PATHS.myCompany}/${company.id}${qs}`)
  }

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.my_company.title', { defaultValue: 'My Company' })}
          subtitle={t('app.my_company.subtitle', {
            defaultValue: 'Operating company profile: legal data, bank details, branding and contacts.',
          })}
          kind={company ? 'action' : 'browse'}
          primaryAction={
            company ? (
              <button type="button" className="btn-primary btn-sm" onClick={openEditor}>
                {t('common.actions.edit', { defaultValue: 'Edit' })}
              </button>
            ) : undefined
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pb-4">
        {error ? (
          <ErrorRecoveryBanner
            info={error}
            onRetry={() => window.location.reload()}
            retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
            {...friendlyErrorBannerSecondary(
              error,
              CRM_APP_PATHS.onboardingCompany,
              t('app.my_company.create', { defaultValue: 'Create my company' }),
            )}
          />
        ) : null}

        {loading ? (
          <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500">
            {t('common.loading')}
          </div>
        ) : company ? (
          <OwnCompanyProfileView
            company={company}
            tab={OWN_COMPANY_PROFILE_TABS.includes(tab) ? tab : 'overview'}
            onTabChange={setTab}
            onEdit={openEditor}
            stats={stats}
            companiesCount={ownCompanies.length}
            companyOptions={ownCompanies.map((item) => ({
              id: item.id,
              name: item.name || item.legal_name || item.id,
            }))}
            onSelectCompany={(id) => void selectCompany(id)}
          />
        ) : (
          <section className="app-surface space-y-3 p-6">
            <h2 className="text-lg font-semibold text-slate-900">
              {t('app.my_company.empty.title', { defaultValue: 'No operating company yet' })}
            </h2>
            <p className="text-sm text-slate-500">
              {t('app.my_company.empty.subtitle', {
                defaultValue:
                  'Create your own company profile first. Client companies do not replace your operating profile.',
              })}
            </p>
            <div className="flex flex-wrap gap-2">
              <Link className="btn-primary" to={CRM_APP_PATHS.onboardingCompany}>
                {t('app.my_company.create', { defaultValue: 'Create my company' })}
              </Link>
            </div>
          </section>
        )}
      </div>
    </PageShell>
  )
}
