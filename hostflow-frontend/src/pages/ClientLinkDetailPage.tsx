import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import {
  listTenantLinks,
  updateTenantLink,
  createPortalLink,
  revokePortalLink,
  type TenantLink,
} from '../api/tenantLinks'
import { useToast } from '../components/Toast'
import { listCompanies } from '../api/client'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useBusinessTerminology } from '../hooks/useBusinessTerminology'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageBreadcrumb } from '../components/nav/PageBreadcrumb'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { useCurrentTenantId } from '../contexts/CurrentTenant'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'

export default function ClientLinkDetailPage() {
  const { linkId } = useParams<{ linkId: string }>()
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const { isEmployerTenant, entitySingular } = useBusinessTerminology()
  const { me } = useAuth()
  const currentTenantId = useCurrentTenantId()
  const { notify } = useToast()
  const tenantId = (currentTenantId ?? (me as { tenant_id?: string })?.tenant_id ?? '').trim()
  const backToListLabel = isEmployerTenant
    ? t('app.companies.actions.back_to_list', { defaultValue: 'Back to companies' })
    : t('app.clients.back_to_list', { defaultValue: 'Back to clients' })
  const notFoundTitle = t('app.clients.not_found_dynamic', {
    defaultValue: '{entity} not found',
    values: { entity: entitySingular },
  })

  const [link, setLink] = useState<TenantLink | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [portalLoading, setPortalLoading] = useState(false)
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<FriendlyErrorInfo | null>(null)

  const load = useCallback(async () => {
    if (!tenantId || !linkId) return
    try {
      setLoading(true)
      setLoadError(null)
      const data = await listTenantLinks(tenantId)
      const found = data.find((l) => l.id === linkId)
      setLink(found ?? null)
      
      // Determine company_id from TenantLink
      if (found) {
        // Priority 1: direct client_company_id
        if (found.client_company_id) {
          setCompanyId(found.client_company_id)
        }
        // Priority 2: handoff_include_company_id (company from client tenant)
        else if (found.handoff_include_company_id) {
          setCompanyId(found.handoff_include_company_id)
        }
        // Priority 3: find company by client_tenant_id
        else if (found.client_tenant_id) {
          try {
            // List companies from agency tenant - they should include linked client tenant companies
            const companies = await listCompanies({ limit: 1000 })
            const company = companies.find((c: any) => c.tenant_id === found.client_tenant_id)
            if (company) {
              setCompanyId(company.id)
            }
          } catch (e) {
            // Ignore errors when fetching companies
            console.warn('Failed to fetch companies for client tenant:', e)
          }
        } else {
          setCompanyId(null)
        }
      } else {
        setCompanyId(null)
      }
    } catch (e: unknown) {
      const fb = t('app.clients.errors.link_load_failed', { defaultValue: 'Failed to load client link' })
      if (!planLimitModal?.showPlanLimitIfNeeded(e, fb)) {
        setLoadError(getFriendlyErrorInfo(e, fb, t))
      }
      setLink(null)
    } finally {
      setLoading(false)
    }
  }, [linkId, planLimitModal, t, tenantId])

  useEffect(() => {
    void load()
  }, [load])

  const handleUpdate = async (payload: { handoff_enabled?: boolean; see_vacancies?: boolean; see_reduced_profiles?: boolean }) => {
    if (!tenantId || !link) return
    setSaving(true)
    try {
      const updated = await updateTenantLink(tenantId, link.id, payload)
      setLink(updated)
      notify({ title: t('common.saved', { defaultValue: 'Сохранено' }), variant: 'success' })
    } catch (e: unknown) {
      const fb = t('app.clients.errors.update_failed', { defaultValue: 'Could not save changes' })
      if (planLimitModal?.showPlanLimitIfNeeded(e, fb)) return
      const fe = getFriendlyErrorInfo(e, fb, t)
      notify({ title: fe.title, variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  const handleCreatePortal = async () => {
    if (!tenantId || !link) return
    setPortalLoading(true)
    try {
      const out = await createPortalLink(tenantId, link.id)
      setLink({ ...link, portal_token: out.token })
      notify({ title: t('app.clients.portal_created', { defaultValue: 'Ссылка создана' }), variant: 'success' })
    } catch (e: unknown) {
      const fb = t('app.clients.errors.portal_create_failed', { defaultValue: 'Could not create portal link' })
      if (planLimitModal?.showPlanLimitIfNeeded(e, fb)) return
      const fe = getFriendlyErrorInfo(e, fb, t)
      notify({ title: fe.title, variant: 'error' })
    } finally {
      setPortalLoading(false)
    }
  }

  const handleRevokePortal = async () => {
    if (!tenantId || !link) return
    setPortalLoading(true)
    try {
      await revokePortalLink(tenantId, link.id)
      setLink({ ...link, portal_token: null })
      notify({ title: t('app.clients.portal_revoked', { defaultValue: 'Ссылка отозвана' }), variant: 'success' })
    } catch (e: unknown) {
      const fb = t('app.clients.errors.portal_revoke_failed', { defaultValue: 'Could not revoke portal link' })
      if (planLimitModal?.showPlanLimitIfNeeded(e, fb)) return
      const fe = getFriendlyErrorInfo(e, fb, t)
      notify({ title: fe.title, variant: 'error' })
    } finally {
      setPortalLoading(false)
    }
  }

  if (!tenantId || !linkId) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка...' })}</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Загрузка...' })}</p>
      </div>
    )
  }

  if (!link) {
    const bannerInfo: FriendlyErrorInfo =
      loadError ??
      ({
        title: notFoundTitle,
        hint: t('app.common.retry_hint'),
      } satisfies FriendlyErrorInfo)
    return (
      <div className="space-y-4">
        <Link to={CRM_APP_PATHS.agencyClients} className="text-sm text-brand-600 hover:underline">
          ← {backToListLabel}
        </Link>
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <ErrorRecoveryBanner
            info={bannerInfo}
            onRetry={() => void load()}
            retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
            {...friendlyErrorBannerSecondary(
              bannerInfo,
              CRM_APP_PATHS.agencyClients,
              t('app.clients.title', { defaultValue: 'Clients' }),
            )}
            compact
          />
        </div>
      </div>
    )
  }

  const rawName = link.company_name ?? (link.features_json as Record<string, unknown>)?.client_display_name ?? link.id
  // `features_json` is `unknown` so the optional chain widens; coerce to string for JSX.
  const name = typeof rawName === 'string' ? rawName : String(rawName ?? '')
  const portalUrl = link.portal_token
    ? `${typeof window !== 'undefined' ? window.location.origin : ''}/client-portal?token=${link.portal_token}`
    : ''

  return (
    <div className="space-y-4">
      <div>
        <Link to={CRM_APP_PATHS.agencyClients} className="text-sm text-brand-600 hover:underline">
          ← {backToListLabel}
        </Link>
      </div>

      <PageBreadcrumb className="max-w-4xl" />

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            {(link.client_company_id || link.handoff_include_company_id || companyId) ? (
              <Link 
                to={`${CRM_APP_PATHS.agencyClients}/${link.client_company_id || link.handoff_include_company_id || companyId}`}
                className="text-xl font-semibold text-brand-600 hover:text-brand-700 hover:underline"
              >
                {name}
              </Link>
            ) : (
              <h1 className="text-xl font-semibold text-slate-900">{name}</h1>
            )}
            {link.client_tenant_id && (
              <p className="mt-1 text-sm text-slate-500">
                {t('app.clients.linked_tenant', { defaultValue: 'Привязан к организации' })}
              </p>
            )}
          </div>
        </div>

        <div className="mt-6 space-y-4">
          <div>
            <span className="block text-sm font-medium text-slate-700">
              {t('app.clients.settings', { defaultValue: 'Настройки доступа' })}
            </span>
            <div className="mt-2 flex flex-wrap gap-6">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={!!link.handoff_enabled}
                  disabled={saving}
                  onChange={(e) => void handleUpdate({ handoff_enabled: e.target.checked })}
                />
                <span className="text-sm">{t('app.clients.handoff_label', { defaultValue: 'Передача кандидатов' })}</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={!!link.see_vacancies}
                  disabled={saving}
                  onChange={(e) => void handleUpdate({ see_vacancies: e.target.checked })}
                />
                <span className="text-sm">{t('app.clients.see_vacancies_label', { defaultValue: 'Видеть вакансии' })}</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={!!link.see_reduced_profiles}
                  disabled={saving}
                  onChange={(e) => void handleUpdate({ see_reduced_profiles: e.target.checked })}
                />
                <span className="text-sm">{t('app.clients.see_reduced_label', { defaultValue: 'Урезанные профили' })}</span>
              </label>
            </div>
          </div>

          <div>
            <span className="block text-sm font-medium text-slate-700">
              {t('app.clients.portal_access', { defaultValue: 'Доступ по ссылке' })}
            </span>
            {link.portal_token ? (
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={portalUrl}
                  className="min-w-[200px] flex-1 rounded border border-slate-200 bg-slate-50 px-2 py-1 text-sm"
                />
                <button type="button" onClick={() => navigator.clipboard.writeText(portalUrl)} className="btn-secondary text-sm">
                  {t('common.copy', { defaultValue: 'Копировать' })}
                </button>
                <button
                  type="button"
                  onClick={handleRevokePortal}
                  disabled={portalLoading}
                  className="btn-danger btn-sm disabled:opacity-50"
                >
                  {t('app.clients.revoke_link', { defaultValue: 'Отозвать' })}
                </button>
              </div>
            ) : (
              <div className="mt-2">
                <button
                  type="button"
                  onClick={handleCreatePortal}
                  disabled={portalLoading}
                  className="btn-secondary text-sm"
                >
                  {portalLoading ? t('common.loading', { defaultValue: '…' }) : t('app.clients.create_portal_link', { defaultValue: 'Создать ссылку' })}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
