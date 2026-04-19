import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  createSeatRequest,
  decidePlatformSeatRequest,
  getPlatformTenant,
  getPlatformTenantModules,
  getTeamOverview,
  listPlatformSeatRequests,
  listSeatRequests,
  updatePlatformTenantModules,
  updateTenantModules,
} from '../../api/tenants'
import type {
  PlatformTenant,
  SeatRequest,
  SeatRequestCreatePayload,
  TeamOverviewResponse,
  TenantModuleSettings,
  TenantModuleSettingsPatch,
} from '../../api/types'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary } from '../../utils/friendlyError'

const ROLE_OPTIONS: { value: SeatRequest['role']; labelKey: string }[] = [
  { value: 'administrator', labelKey: 'app.settings.team.form.roles.administrator' },
  { value: 'supervisor', labelKey: 'app.settings.team.form.roles.supervisor' },
  { value: 'recruiter', labelKey: 'app.settings.team.form.roles.recruiter' },
  { value: 'client_manager', labelKey: 'app.settings.team.form.roles.client_manager' },
  { value: 'client_processor', labelKey: 'app.admin.users.roles.client_processor' },
  { value: 'viewer', labelKey: 'app.settings.team.form.roles.viewer' },
]

type SeatFormState = {
  role: SeatRequest['role']
  requested_count: string
  message: string
}

const DEFAULT_FORM: SeatFormState = {
  role: 'recruiter',
  requested_count: '1',
  message: '',
}

type TeamManagementPanelProps = {
  tenantId?: string | null
  showHeader?: boolean
  compact?: boolean
}

function formatErrorMessage(err: unknown, fallback: string): string {
  if (typeof (err as any)?.message === 'string' && !(err as any)?.response) {
    return (err as any).message
  }
  const detail = (err as any)?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length) {
    return detail.map((entry) => (typeof entry === 'string' ? entry : JSON.stringify(entry))).join(', ')
  }
  return fallback
}

export function TeamManagementPanel({
  tenantId,
  showHeader = true,
  compact = false,
}: TeamManagementPanelProps) {
  const { t } = useI18n()
  const [overview, setOverview] = useState<TeamOverviewResponse | null>(null)
  const [platformSummary, setPlatformSummary] = useState<PlatformTenant | null>(null)
  const [modules, setModules] = useState<TenantModuleSettings | null>(null)
  const [seatRequests, setSeatRequests] = useState<SeatRequest[]>([])
  const [seatForm, setSeatForm] = useState<SeatFormState>({ ...DEFAULT_FORM })
  const [seatSubmitting, setSeatSubmitting] = useState(false)
  const [seatError, setSeatError] = useState<string | null>(null)
  const [modulesSaving, setModulesSaving] = useState(false)
  const [modulesError, setModulesError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [seatLoading, setSeatLoading] = useState(false)
  const [seatActionLoading, setSeatActionLoading] = useState(false)
  const isPlatformView = Boolean(tenantId)

  const loadSeatRequests = useCallback(async () => {
    if (!isPlatformView) {
      setSeatLoading(true)
      try {
        const history = await listSeatRequests()
        setSeatRequests(history)
      } catch (err) {
        setSeatError(formatErrorMessage(err, t('app.settings.team.history.subtitle')))
      } finally {
        setSeatLoading(false)
      }
      return
    }
    if (!tenantId) return
    setSeatLoading(true)
    setSeatError(null)
    try {
      const data = await listPlatformSeatRequests(tenantId)
      setSeatRequests(data)
    } catch (err) {
      setSeatError(formatErrorMessage(err, t('app.platform.tenants.seat_requests.errors.load_failed')))
    } finally {
      setSeatLoading(false)
    }
  }, [isPlatformView, tenantId, t])

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        if (isPlatformView && tenantId) {
          const summary = await getPlatformTenant(tenantId)
          setPlatformSummary(summary)
          const mods = await getPlatformTenantModules(tenantId)
          setModules(mods)
        } else {
          const data = await getTeamOverview()
          setOverview(data)
          setModules(data.modules)
        }
        await loadSeatRequests()
      } catch (err) {
        console.warn('[TeamManagement] overview failed', err)
        setError(t('app.settings.team.errors.load_failed'))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [tenantId, isPlatformView, loadSeatRequests, t])

  const seatCards = useMemo(() => {
    const usage = overview?.usage ?? platformSummary?.usage
    const license = overview?.license ?? platformSummary?.license ?? null
    if (!usage) return []
    return [
      {
        id: 'recruiters',
        label: t('app.settings.team.usage.recruiters'),
        used: usage.recruiter_count,
        limit: license?.max_recruiters ?? 0,
      },
      {
        id: 'supervisors',
        label: t('app.settings.team.usage.supervisors'),
        used: usage.supervisor_count,
        limit: license?.max_supervisors ?? 0,
      },
      {
        id: 'client_managers',
        label: t('app.settings.team.usage.client_managers'),
        used: usage.client_manager_count,
        limit: license?.max_client_managers ?? 0,
      },
      {
        id: 'viewers',
        label: t('app.settings.team.usage.viewers'),
        used: usage.viewer_count,
        limit: license?.max_viewers ?? 0,
      },
    ]
  }, [overview, platformSummary, t])

  const handleToggleModule = async (key: keyof TenantModuleSettings) => {
    if (!modules) return
    setModulesSaving(true)
    setModulesError(null)
    const patch: TenantModuleSettingsPatch = { [key]: !modules[key] }
    try {
      const updated = isPlatformView && tenantId
        ? await updatePlatformTenantModules(tenantId, patch)
        : await updateTenantModules(patch)
      setModules(updated)
    } catch (err) {
      const fallback = t('app.settings.team.errors.modules_save_failed')
      const message = formatErrorMessage(err, fallback)
      setModulesError(message)
    } finally {
      setModulesSaving(false)
    }
  }

  const handleSeatFormChange = (field: keyof SeatFormState, value: string) => {
    setSeatForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleSeatSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (isPlatformView) return
    setSeatSubmitting(true)
    setSeatError(null)
    try {
      const payload: SeatRequestCreatePayload = {
        role: seatForm.role,
        requested_count: Number(seatForm.requested_count) || 0,
        message: seatForm.message.trim() || undefined,
      }
      await createSeatRequest(payload)
      setSeatForm({ ...DEFAULT_FORM })
      await loadSeatRequests()
    } catch (err) {
      console.warn('[TeamManagement] seat request failed', err)
      setSeatError(t('app.settings.team.errors.seat_request_failed'))
    } finally {
      setSeatSubmitting(false)
    }
  }

  const handleSeatDecision = async (request: SeatRequest, status: 'approved' | 'rejected') => {
    if (!isPlatformView || !tenantId) return
    const confirmText = t('app.platform.tenants.seat_requests.actions.confirm', {
      values: {
        status: t(`app.platform.tenants.seat_requests.status.${status}`),
        count: request.requested_count,
      },
    })
    if (!window.confirm(confirmText)) return
    const note = window.prompt(t('app.platform.tenants.seat_requests.actions.notes_prompt'), '')
    setSeatActionLoading(true)
    setSeatError(null)
    try {
      await decidePlatformSeatRequest(tenantId, request.id, {
        status,
        resolution_notes: note?.trim() ? note.trim() : undefined,
      })
      await loadSeatRequests()
    } catch (err) {
      setSeatError(formatErrorMessage(err, t('app.platform.tenants.seat_requests.errors.action_failed')))
    } finally {
      setSeatActionLoading(false)
    }
  }

  if (loading) {
    return <div className="text-sm text-slate-500">{t('common.loading')}</div>
  }

  if (error) {
    const loadErr: FriendlyErrorInfo = {
      title: error,
      hint: t('app.common.retry_hint'),
    }
    return (
      <ErrorRecoveryBanner
        info={loadErr}
        onRetry={() => window.location.reload()}
        retryLabel={t('common.actions.refresh')}
        {...friendlyErrorBannerSecondary(loadErr, CRM_APP_PATHS.settingsTeam, t('app.settings.team.title'))}
        compact
      />
    )
  }

  const license = overview?.license ?? platformSummary?.license ?? null
  const tenantLabel = isPlatformView
    ? platformSummary?.workspace_label || platformSummary?.name || platformSummary?.slug || null
    : overview?.tenant?.workspace_label || overview?.tenant?.name || overview?.tenant?.slug || null

  const modulesErrBanner: FriendlyErrorInfo | null = modulesError
    ? {
        title: modulesError,
        hint: t('app.common.retry_hint'),
      }
    : null
  const seatErrBanner: FriendlyErrorInfo | null = seatError
    ? {
        title: seatError,
        hint: t('app.common.retry_hint'),
      }
    : null

  return (
    <div className={compact ? 'space-y-4' : 'space-y-4'}>
      {showHeader && (
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            {t('app.settings.team.title')}
          </h1>
          <p className="text-sm text-slate-500">{t('app.settings.team.subtitle')}</p>
        </div>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-slate-900">
              {t('app.settings.team.usage.title')}
            </div>
            {tenantLabel && <div className="text-xs text-slate-500">{tenantLabel}</div>}
          </div>
          {license?.plan && (
            <span className="badge">
              {license.plan}
            </span>
          )}
        </div>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          {seatCards.map((card) => (
            <SeatUsageCard key={card.id} label={card.label} used={card.used} limit={card.limit} />
          ))}
        </div>
        {license && (
          <dl className="grid gap-3 md:grid-cols-3 pt-2 text-sm text-slate-700">
            <div>
              <dt className="text-xs uppercase text-slate-400">{t('app.platform.tenants.license.plan')}</dt>
              <dd className="font-medium text-slate-900">{license.plan || '—'}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-400">{t('app.platform.tenants.license.expires_at')}</dt>
              <dd className="font-medium text-slate-900">
                {license.expires_at ? new Date(license.expires_at).toLocaleDateString() : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-400">{t('app.platform.tenants.license.max_companies')}</dt>
              <dd className="font-medium text-slate-900">{license.max_companies ?? 0}</dd>
            </div>
          </dl>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">{t('app.platform.tenants.modules.title')}</h2>
          {modulesSaving && <span className="text-xs text-slate-500">{t('common.saving')}</span>}
        </div>
        <p className="text-xs text-slate-500">{t('app.platform.tenants.modules.description')}</p>
        {modulesErrBanner && (
          <div className="mt-2">
            <ErrorRecoveryBanner
              info={modulesErrBanner}
              onRetry={() => window.location.reload()}
              retryLabel={t('common.actions.refresh')}
              {...friendlyErrorBannerSecondary(
                modulesErrBanner,
                CRM_APP_PATHS.settingsTeam,
                t('app.platform.tenants.modules.title'),
              )}
              compact
            />
          </div>
        )}
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {modules &&
            (Object.keys(modules) as Array<keyof TenantModuleSettings>).map((moduleKey) => (
              <label
                key={moduleKey}
                className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm text-slate-700"
              >
                <span>{t(`app.platform.tenants.modules.items.${moduleKey}`)}</span>
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-brand-600"
                  checked={modules[moduleKey]}
                  onChange={() => handleToggleModule(moduleKey)}
                  disabled={modulesSaving}
                />
              </label>
            ))}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              {t('app.platform.tenants.seat_requests.title')}
            </h2>
            <p className="text-xs text-slate-500">
              {t('app.platform.tenants.seat_requests.subtitle')}
            </p>
          </div>
          <button
            type="button"
            className="btn-secondary btn-xs"
            onClick={() => void loadSeatRequests()}
            disabled={seatLoading}
          >
            {seatLoading ? t('common.loading') : t('app.platform.tenants.seat_requests.actions.refresh')}
          </button>
        </div>
        {seatErrBanner && (
          <ErrorRecoveryBanner
            info={seatErrBanner}
            onRetry={() => void loadSeatRequests()}
            retryLabel={t('app.platform.tenants.seat_requests.actions.refresh')}
            {...friendlyErrorBannerSecondary(
              seatErrBanner,
              CRM_APP_PATHS.settingsTeam,
              t('app.platform.tenants.seat_requests.title'),
            )}
            compact
          />
        )}
        {!isPlatformView && (
          <form className="space-y-3 rounded border border-slate-100 bg-slate-50 p-3" onSubmit={handleSeatSubmit}>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.settings.team.form.title')}
            </div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.settings.team.form.role')}
              <select
                className="input mt-1"
                value={seatForm.role}
                onChange={(event) => handleSeatFormChange('role', event.target.value)}
              >
                {ROLE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {t(option.labelKey)}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.settings.team.form.count')}
              <input
                className="input mt-1"
                type="number"
                min="1"
                name="requested_count"
                autoComplete="off"
                value={seatForm.requested_count}
                onChange={(event) => handleSeatFormChange('requested_count', event.target.value)}
              />
            </label>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.settings.team.form.message')}
              <textarea
                className="textarea mt-1 min-h-[90px]"
                value={seatForm.message}
                onChange={(event) => handleSeatFormChange('message', event.target.value)}
              />
            </label>
            <button type="submit" className="btn-primary" disabled={seatSubmitting}>
              {seatSubmitting ? t('common.saving') : t('app.settings.team.form.submit')}
            </button>
            {seatError && <div className="alert-error text-xs">{seatError}</div>}
          </form>
        )}
        <div className="space-y-3">
          {seatLoading ? (
            <div className="text-sm text-slate-500">{t('common.loading')}</div>
          ) : seatRequests.length === 0 ? (
            <div className="rounded border border-slate-100 bg-slate-50 px-3 py-3 text-xs text-slate-500">
              {t('app.platform.tenants.seat_requests.empty')}
            </div>
          ) : (
            seatRequests.map((request) => (
              <div key={request.id} className="rounded border border-slate-100 p-3 text-sm text-slate-700 space-y-1">
                <div className="flex flex-wrap items-center justify-between text-xs text-slate-500">
                  <span>{new Date(request.created_at).toLocaleString()}</span>
                  <span className={`badge ${request.status === 'approved' ? 'text-emerald-700' : request.status === 'rejected' ? 'text-rose-700' : 'text-amber-700'}`}>
                    {t(`app.platform.tenants.seat_requests.status.${request.status}`)}
                  </span>
                </div>
                <div className="font-semibold">
                  {t('app.platform.tenants.seat_requests.summary', {
                    values: {
                      role: t(`app.settings.team.form.roles.${request.role}`),
                      count: request.requested_count,
                    },
                  })}
                </div>
                {request.message && <p className="text-xs text-slate-500">{request.message}</p>}
                {request.resolution_notes && (
                  <p className="text-xs text-slate-400">
                    {t('app.platform.tenants.seat_requests.resolution', { values: { notes: request.resolution_notes } })}
                  </p>
                )}
                {isPlatformView && request.status === 'pending' && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={() => void handleSeatDecision(request, 'approved')}
                      disabled={seatActionLoading}
                    >
                      {seatActionLoading ? t('common.saving') : t('app.platform.tenants.seat_requests.actions.approve')}
                    </button>
                    <button
                      type="button"
                      className="btn-danger"
                      onClick={() => void handleSeatDecision(request, 'rejected')}
                      disabled={seatActionLoading}
                    >
                      {seatActionLoading ? t('common.saving') : t('app.platform.tenants.seat_requests.actions.reject')}
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  )
}

export default function BillingTeamPage() {
  const { t } = useI18n()
  return (
    <div className="space-y-4">
      <SettingsSubpageHeader
        backHref={CRM_APP_PATHS.settings}
        backLabel={t('admin.settings.subpage.back_all')}
        kicker={t('admin.settings.subpage.kicker_workspace_setup')}
        title={t('app.settings.team.title')}
        subtitle={t('app.settings.team.subtitle')}
      />
      <TeamManagementPanel showHeader={false} />
    </div>
  )
}

function SeatUsageCard({
  label,
  used,
  limit,
}: {
  label: string
  used: number
  limit: number
}) {
  const percentage = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : used > 0 ? 100 : 0
  const displayLimit = limit > 0 ? limit : '∞'
  const warn = limit > 0 && used / limit >= 0.9

  return (
    <div className="rounded border border-slate-100 p-3">
      <div className="text-xs uppercase text-slate-400">{label}</div>
      <div className="mt-2 h-2 rounded-full bg-slate-100">
        <div
          className={`h-2 rounded-full ${warn ? 'bg-amber-500' : 'bg-brand-500'}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="mt-2 text-sm font-semibold text-slate-900">
        {used}
        <span className="ml-1 text-xs text-slate-500">/ {displayLimit}</span>
      </div>
    </div>
  )
}
