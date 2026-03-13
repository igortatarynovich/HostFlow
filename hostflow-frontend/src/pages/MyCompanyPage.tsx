import { useEffect, useMemo, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { listCompanies } from '../api/client'
import { getBillingSummary, type BillingSummary } from '../api/billing'
import type { Company } from '../api/types'
import { useAuth } from '../store/useAuth'
import { useI18n } from '../i18n'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'

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
  const navigate = useNavigate()
  const [companies, setCompanies] = useState<Company[]>([])
  const [billing, setBilling] = useState<BillingSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const [companiesData, billingData] = await Promise.all([
          listCompanies({ limit: 500 }),
          getBillingSummary(),
        ])
        if (!mounted) return
        setCompanies(Array.isArray(companiesData) ? companiesData : [])
        setBilling(billingData)
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
  }, [])

  const managedOperatingCompanies = useMemo(() => {
    const userId = String((me as any)?.sub || '').trim()
    return companies.filter((company) => isOperatingCompany(company) && isManagedByUser(company, userId))
  }, [companies, me])

  if (!loading && !error && managedOperatingCompanies.length === 1) {
    return <Navigate to={`/app/my-company/${managedOperatingCompanies[0].id}`} replace />
  }

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
          <button className="btn-primary bg-white text-slate-900 hover:bg-white/90" onClick={() => navigate('/app/onboarding/company')}>
            {t('app.my_company.create', { defaultValue: 'Create my company' })}
          </button>
        </div>
        <div className="mt-6 grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-white/20 bg-white/10 p-4">
            <div className="text-sm text-white/80">{t('app.my_company.cards.operating_count', { defaultValue: 'Operating companies' })}</div>
            <div className="text-3xl font-semibold">{managedOperatingCompanies.length}</div>
          </div>
          <div className="rounded-2xl border border-white/20 bg-white/10 p-4">
            <div className="text-sm text-white/80">{t('app.my_company.cards.limit', { defaultValue: 'Plan limit' })}</div>
            <div className="text-3xl font-semibold">{billing?.license?.max_companies ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-white/20 bg-white/10 p-4">
            <div className="text-sm text-white/80">{t('app.my_company.cards.available', { defaultValue: 'Available slots' })}</div>
            <div className="text-3xl font-semibold">
              {Math.max((billing?.license?.max_companies ?? 0) - managedOperatingCompanies.length, 0)}
            </div>
          </div>
        </div>
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
            <button className="btn-primary" onClick={() => navigate('/app/onboarding/company')}>
              {t('app.my_company.create', { defaultValue: 'Create my company' })}
            </button>
            <Link className="btn-secondary" to="/app/settings/billing">
              {t('app.my_company.open_billing', { defaultValue: 'Open billing' })}
            </Link>
          </div>
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
                  <dd className="mt-1 text-slate-900">{String(company.owner_user_id || '-')}</dd>
                </div>
              </dl>
              <div className="flex flex-wrap gap-2 pt-2">
                <Link className="btn-primary" to={`/app/my-company/${company.id}`}>
                  {t('common.actions.open', { defaultValue: 'Open' })}
                </Link>
                <Link className="btn-secondary" to="/app/invoices">
                  {t('app.my_company.open_invoices', { defaultValue: 'Open invoices' })}
                </Link>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  )
}
