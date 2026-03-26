import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listCompanies } from '../api/client'
import { getBillingSummary, type BillingSummary } from '../api/billing'
import { getTeamOverview } from '../api/tenants'
import type { Company } from '../api/types'
import { useAuth } from '../store/useAuth'
import { useI18n } from '../i18n'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { usePermissions } from '../hooks/usePermissions'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

function isOperatingCompany(company: Company) {
  const role = String((company.extra as Record<string, any> | undefined)?.company_role || '').trim().toLowerCase()
  return role === 'operating'
}

function isManagedByUser(company: Company, userId: string) {
  const actor = String(userId || '').trim()
  if (!actor) return false
  return [company.owner_user_id, company.manager_user_id].some((value) => String(value || '').trim() === actor)
}

export default function MyCompanyPage() {
  const { t } = useI18n()
  const { me } = useAuth()
  const { can, role } = usePermissions()
  const canLoadTeamOverview = role === 'administrator' || role === 'supervisor'
  const navigate = useNavigate()
  const [companies, setCompanies] = useState<Company[]>([])
  const [billing, setBilling] = useState<BillingSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [userLabelById, setUserLabelById] = useState<Record<string, string>>({})

  useEffect(() => {
    let mounted = true
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const [companiesData, billingData, team] = await Promise.all([
          listCompanies({ limit: 500 }),
          getBillingSummary(),
          canLoadTeamOverview ? getTeamOverview().catch(() => null) : Promise.resolve(null),
        ])
        if (!mounted) return
        setCompanies(Array.isArray(companiesData) ? companiesData : [])
        setBilling(billingData)
        const map: Record<string, string> = {}
        const members = Array.isArray((team as any)?.members) ? (team as any).members : []
        members.forEach((member: any) => {
          const id = String(member?.id || member?.user_id || '').trim()
          if (!id) return
          const label = String(member?.full_name || member?.email || id).trim()
          map[id] = label
        })
        setUserLabelById(map)
      } catch (err: any) {
        if (!mounted) return
        setError(err?.response?.data?.detail || err?.message || 'Failed to load company profiles')
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [canLoadTeamOverview])

  const managedOperatingCompanies = useMemo(() => {
    const userId = String((me as any)?.sub || '').trim()
    return companies.filter((company) => isOperatingCompany(company) && isManagedByUser(company, userId))
  }, [companies, me])

  const formatUserLabel = (id?: string | null) => {
    const key = String(id || '').trim()
    if (!key) return '-'
    const meId = String((me as any)?.sub || '').trim()
    const base = userLabelById[key] || key
    if (meId && key === meId) return t('app.common.you', { defaultValue: 'You' })
    return base
  }

  const primaryCompanyId = managedOperatingCompanies[0]?.id || ''
  const effectiveOperatingLimit = billing?.company_slots?.effective_limit ?? billing?.license?.max_companies ?? 0
  const availableOperatingSlots = billing?.company_slots?.unlimited
    ? 0
    : Math.max((billing?.company_slots?.available ?? effectiveOperatingLimit - managedOperatingCompanies.length), 0)
  const hasAvailableOperatingSlots = Boolean(billing?.company_slots?.unlimited) || availableOperatingSlots > 0
  const usedOperatingSlots = Number(billing?.company_slots?.used ?? managedOperatingCompanies.length)
  const recommendedExtraSlots = Math.max(1, usedOperatingSlots - effectiveOperatingLimit + 1)
  const billingCompanySlotsPath = `${CRM_APP_PATHS.settingsBilling}?focus=company-slots&recommended_extra_slots=${recommendedExtraSlots}`
  const operatingSlotsOverflow = !billing?.company_slots?.unlimited && effectiveOperatingLimit > 0 && usedOperatingSlots > effectiveOperatingLimit
  const operatingSlotsMissing = operatingSlotsOverflow ? Math.max(1, usedOperatingSlots - effectiveOperatingLimit) : 0

  return (
    <div className="flex h-full w-full flex-col gap-4 p-6">
      <section className="rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-700 p-6 text-white shadow-card">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1">
            <p className="text-2xl font-semibold">{t('app.my_company.title', { defaultValue: 'My Company' })}</p>
            <p className="text-sm text-white/80">
              {t(
                'app.my_company.subtitle',
                { defaultValue: 'Your operating company profiles for invoicing, contracts, legal data and branding.' },
              )}
            </p>
          </div>
          <button
            className="btn-primary bg-white text-slate-900 hover:bg-white/90"
            onClick={() =>
              navigate(hasAvailableOperatingSlots ? CRM_APP_PATHS.onboardingCompany : billingCompanySlotsPath)
            }
          >
            {hasAvailableOperatingSlots
              ? t('app.my_company.create', { defaultValue: 'Create my company' })
              : t('app.my_company.open_billing', { defaultValue: 'Open billing' })}
          </button>
        </div>
        <div className="mt-6 grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-white/20 bg-white/10 p-4">
            <div className="text-sm text-white/80">{t('app.my_company.cards.operating_count', { defaultValue: 'Operating companies' })}</div>
            <div className="text-3xl font-semibold">{managedOperatingCompanies.length}</div>
          </div>
          <div className="rounded-2xl border border-white/20 bg-white/10 p-4">
            <div className="text-sm text-white/80">{t('app.my_company.cards.limit', { defaultValue: 'Plan limit' })}</div>
            <div className="text-3xl font-semibold">{billing?.company_slots?.unlimited ? '∞' : effectiveOperatingLimit}</div>
          </div>
          <div className="rounded-2xl border border-white/20 bg-white/10 p-4">
            <div className="text-sm text-white/80">{t('app.my_company.cards.available', { defaultValue: 'Available slots' })}</div>
            <div className="text-3xl font-semibold">{billing?.company_slots?.unlimited ? '∞' : availableOperatingSlots}</div>
          </div>
        </div>
        {operatingSlotsOverflow ? (
          <div className="mt-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <p className="font-medium">
              {t('app.my_company.cards.overflow_title', {
                defaultValue: 'Operating companies are over your active slot limit',
              })}
            </p>
            <p className="mt-1">
              {t('app.my_company.cards.overflow_text', {
                defaultValue:
                  'Existing data is preserved, but creating new operating companies is blocked until you add at least {count} slot(s).',
                values: { count: operatingSlotsMissing },
              })}
            </p>
            <div className="mt-2">
              <Link className="btn-secondary btn-sm" to={billingCompanySlotsPath}>
                {t('app.my_company.open_billing', { defaultValue: 'Open billing' })}
              </Link>
            </div>
          </div>
        ) : null}
      </section>

      {error && (
        <ErrorRecoveryBanner
          info={{
            title: error,
            hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
          }}
          onRetry={() => window.location.reload()}
          retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
        />
      )}

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500">
          {t('common.loading', { defaultValue: 'Loading...' })}
        </div>
      ) : managedOperatingCompanies.length > 0 ? (
        <section className="app-surface space-y-3 p-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              {t('app.my_company.workspace.title', { defaultValue: 'Owner profile workspace' })}
            </h2>
            <p className="text-sm text-slate-500">
              {t('app.my_company.workspace.subtitle', {
                defaultValue: 'Quick actions for legal entity data, billing setup, bank details and branding.',
              })}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link className="btn-primary" to={`${CRM_APP_PATHS.myCompany}/${primaryCompanyId}?section=legal`}>
              {t('app.my_company.workspace.legal', { defaultValue: 'Legal' })}
            </Link>
            <Link
              className="btn-secondary"
              to={`${CRM_APP_PATHS.myCompany}/${primaryCompanyId}?section=billing`}
            >
              {t('app.my_company.workspace.billing', { defaultValue: 'Billing' })}
            </Link>
            <Link
              className="btn-secondary"
              to={`${CRM_APP_PATHS.myCompany}/${primaryCompanyId}?section=bank_accounts`}
            >
              {t('app.my_company.workspace.bank_accounts', { defaultValue: 'Bank Accounts' })}
            </Link>
            <Link
              className="btn-secondary"
              to={`${CRM_APP_PATHS.myCompany}/${primaryCompanyId}?section=branding`}
            >
              {t('app.my_company.workspace.branding', { defaultValue: 'Branding' })}
            </Link>
          </div>
        </section>
      ) : managedOperatingCompanies.length === 0 ? (
        <section className="app-surface space-y-3 p-6">
          <h2 className="text-lg font-semibold text-slate-900">{t('app.my_company.empty.title', { defaultValue: 'No operating company yet' })}</h2>
          <p className="text-sm text-slate-500">
            {t(
              'app.my_company.empty.subtitle',
              { defaultValue: 'Create your own company profile first. Client companies do not replace your operating profile.' },
            )}
          </p>
          <div className="flex flex-wrap gap-2">
            {hasAvailableOperatingSlots ? (
              <button className="btn-primary" onClick={() => navigate(CRM_APP_PATHS.onboardingCompany)}>
                {t('app.my_company.create', { defaultValue: 'Create my company' })}
              </button>
            ) : null}
            <Link className="btn-secondary" to={billingCompanySlotsPath}>
              {t('app.my_company.open_billing', { defaultValue: 'Open billing' })}
            </Link>
          </div>
          {!hasAvailableOperatingSlots ? (
            <p className="text-xs text-amber-700">
              {t('app.my_company.empty.limit_reached', {
                defaultValue: 'Operating company slots are fully used. Add an extra slot in Billing to create another company.',
              })}
            </p>
          ) : null}
        </section>
      ) : (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {managedOperatingCompanies.map((company) => (
            <article key={company.id} className="app-surface space-y-3 p-6">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{company.legal_name || company.name}</h2>
                <p className="text-sm text-slate-500">{company.tax_id || t('app.my_company.missing_tax_id', { defaultValue: 'Tax ID not set yet' })}</p>
              </div>
              <dl className="space-y-2 text-sm">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.my_company.card.business_type', { defaultValue: 'Business type' })}</dt>
                  <dd className="mt-1 text-slate-900">{String((company.extra as Record<string, any> | undefined)?.company_type || '-')}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.my_company.card.email', { defaultValue: 'Billing / contact email' })}</dt>
                  <dd className="mt-1 text-slate-900">{company.email || '-'}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.my_company.card.owner', { defaultValue: 'Owner' })}</dt>
                  <dd className="mt-1 text-slate-900">{formatUserLabel(company.owner_user_id)}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t('app.my_company.card.manager', { defaultValue: 'Manager' })}</dt>
                  <dd className="mt-1 text-slate-900">{formatUserLabel(company.manager_user_id)}</dd>
                </div>
              </dl>
              <div className="flex flex-wrap gap-2 pt-2">
                <Link className="btn-primary" to={`${CRM_APP_PATHS.myCompany}/${company.id}`}>
                  {t('common.actions.open', { defaultValue: 'Open' })}
                </Link>
                <Link className="btn-secondary" to={CRM_APP_PATHS.invoices}>
                  {t('app.my_company.open_invoices', { defaultValue: 'Open invoices' })}
                </Link>
                {can('admin.companyAcl') ? (
                  <Link className="btn-secondary" to={CRM_APP_PATHS.settingsCompanyAccess}>
                    {t('app.my_company.manage_access', { defaultValue: 'Manage access' })}
                  </Link>
                ) : null}
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  )
}
