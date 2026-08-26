/**
 * Tenant organization hub — workspace-level controls.
 *
 * Owns: subscription, company slots, modules, users, list of OwnCompanies (switch/create),
 * billing document entry points.
 * Does NOT own: OwnCompany legal/bank/branding/contacts — those live only on `/app/my-company`.
 */
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  IconBuilding,
  IconChevronRight,
  IconCreditCard,
  IconFileText,
  IconUsers,
} from '@tabler/icons-react'
import { getBillingSummary, type BillingSummary } from '../api/billing'
import {
  listOwnCompanies,
  setActiveOwnCompany,
  type OwnCompanyRecord,
} from '../api/client'
import { getTeamOverview } from '../api/tenants'
import type { AdminUser, TenantModuleSettings, TeamOverviewResponse } from '../api/types'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { canUseTeamOverviewLane } from '../auth/trustRoles'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { PageShell, PageShellHeader } from '../components/layout'
import { PageHeader } from '../components/nav/PageHeader'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import { usePermissions } from '../hooks/usePermissions'
import { useI18n } from '../i18n'
import { useAuth } from '../store/useAuth'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../utils/friendlyError'

const MODULE_KEYS: Array<keyof TenantModuleSettings> = [
  'candidates',
  'companies',
  'vacancies',
  'documents',
  'leads',
  'services',
  'hr',
  'client_portal',
]

function initials(label: string): string {
  const parts = label.trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase()
}

function formatPeriod(start: string | null | undefined, end: string | null | undefined, locale: string): string {
  const fmt = (value: string | null | undefined) => {
    if (!value) return null
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return null
    return date.toLocaleDateString(locale, { day: '2-digit', month: 'short', year: 'numeric' })
  }
  const a = fmt(start)
  const b = fmt(end)
  if (a && b) return `${a} — ${b}`
  return a || b || '—'
}

function planLabel(billing: BillingSummary | null): string {
  const code = billing?.subscription?.plan_code || billing?.license?.plan || ''
  if (!code) return '—'
  return code.charAt(0).toUpperCase() + code.slice(1)
}

function subscriptionStatusTone(status: string | undefined): 'ok' | 'warn' | 'muted' {
  const s = String(status || '').toLowerCase()
  if (['active', 'trialing', 'trial'].includes(s)) return 'ok'
  if (['past_due', 'unpaid', 'incomplete'].includes(s)) return 'warn'
  return 'muted'
}

function Donut({ used, total }: { used: number; total: number }) {
  const safeTotal = total > 0 ? total : 0
  const ratio = safeTotal > 0 ? Math.min(1, Math.max(0, used / safeTotal)) : 0
  const size = 132
  const stroke = 14
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const dash = c * ratio
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mx-auto block" aria-hidden>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="currentColor"
        className="text-brand-600"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={`${dash} ${c - dash}`}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
    </svg>
  )
}

export default function OrganizationHubPage() {
  const { t, locale } = useI18n()
  const { me } = useAuth()
  const { can, role, rawRole, presetId } = usePermissions()
  const navigate = useNavigate()
  const planLimitModal = usePlanLimitModal()
  const canLoadTeam =
    canUseTeamOverviewLane({ role: rawRole || role, presetId }) ||
    can('admin.users') ||
    can('users.view')
  const canLoadBilling = can('admin.users')
  const dateLocale = locale === 'pl' ? 'pl-PL' : locale === 'ru' ? 'ru-RU' : 'en-GB'

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [companies, setCompanies] = useState<OwnCompanyRecord[]>([])
  const [billing, setBilling] = useState<BillingSummary | null>(null)
  const [team, setTeam] = useState<TeamOverviewResponse | null>(null)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const [ownRes, billingRes, teamRes] = await Promise.all([
          listOwnCompanies().catch(() => ({ items: [] as OwnCompanyRecord[] })),
          canLoadBilling ? getBillingSummary().catch(() => null) : Promise.resolve(null),
          canLoadTeam ? getTeamOverview().catch(() => null) : Promise.resolve(null),
        ])
        if (!mounted) return
        setCompanies(Array.isArray(ownRes?.items) ? ownRes.items.filter((c) => !c.is_archived) : [])
        setBilling(billingRes)
        setTeam(teamRes)
      } catch (err: any) {
        if (!mounted) return
        const fb = t('app.organization.errors.load_failed', { defaultValue: 'Failed to load organization hub' })
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
  }, [canLoadBilling, canLoadTeam, planLimitModal, t])

  const slots = billing?.company_slots
  const usedSlots = Math.max(
    Number(slots?.used ?? 0),
    companies.length,
  )
  const limitSlots = slots?.unlimited
    ? 0
    : Number(slots?.effective_limit ?? billing?.license?.max_companies ?? 0)
  const availableSlots = slots?.unlimited
    ? null
    : Math.max(limitSlots - usedSlots, 0)
  const subStatus = billing?.subscription?.status
  const statusTone = subscriptionStatusTone(subStatus)
  const modules = team?.modules
  const enabledModules = MODULE_KEYS.filter((key) => Boolean(modules?.[key]))
  const members = useMemo(() => {
    const list = Array.isArray(team?.members) ? team!.members : []
    return list.filter((m) => m.status === 'active' || m.is_active)
  }, [team])
  const avatarMembers = members.slice(0, 6)
  const extraMembers = Math.max(members.length - avatarMembers.length, 0)
  const tenantName = team?.tenant?.workspace_label || team?.tenant?.name || me?.tenant_id || '—'
  const owner =
    members.find((m) => String(m.role || '').toLowerCase() === 'administrator') ||
    members[0] ||
    null

  const paymentPaid =
    ['active', 'trialing', 'trial'].includes(String(subStatus || '').toLowerCase()) &&
    !billing?.subscription?.gate?.side_effects_blocked

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.organization.title', { defaultValue: 'Organization' })}
          subtitle={t('app.organization.subtitle', {
            defaultValue: 'Manage workspace subscription, modules, users and operating companies.',
          })}
          kind="browse"
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
        {error ? (
          <ErrorRecoveryBanner
            info={error}
            onRetry={() => window.location.reload()}
            retryLabel={t('common.actions.retry', { defaultValue: 'Retry' })}
            {...friendlyErrorBannerSecondary(
              error,
              CRM_APP_PATHS.settingsBilling,
              t('app.nav.items.settings_billing', { defaultValue: 'Billing' }),
            )}
          />
        ) : null}

        {loading ? (
          <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500">
            {t('common.loading')}
          </div>
        ) : (
          <div className="grid gap-4 xl:grid-cols-3">
            {/* Identity */}
            <section className="app-surface space-y-4 p-5 xl:col-span-1">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full bg-brand-700 text-lg font-semibold text-white">
                    {team?.tenant?.logo_url ? (
                      <img src={team.tenant.logo_url} alt="" className="h-full w-full object-cover" />
                    ) : (
                      initials(String(tenantName))
                    )}
                  </div>
                  <div className="min-w-0">
                    <h2 className="truncate text-lg font-semibold text-slate-900">{tenantName}</h2>
                    <p className="text-sm text-slate-500">
                      {t('app.organization.identity.workspace', { defaultValue: 'Workspace' })}
                    </p>
                  </div>
                </div>
              </div>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-500">{t('app.organization.identity.companies', { defaultValue: 'Companies' })}</dt>
                  <dd className="font-medium text-slate-900">{companies.length}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-500">{t('app.organization.identity.owner', { defaultValue: 'Owner' })}</dt>
                  <dd className="max-w-[60%] truncate text-right font-medium text-slate-900">
                    {owner?.full_name || owner?.email || '—'}
                  </dd>
                </div>
              </dl>
              <p className="text-xs text-slate-500">
                {t('app.organization.identity.hint', {
                  defaultValue: 'Legal entity details live in each company profile, not here.',
                })}
              </p>
            </section>

            {/* Subscription */}
            <section className="app-surface flex flex-col space-y-3 p-5">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-base font-semibold text-slate-900">
                  {t('app.organization.subscription.title', { defaultValue: 'Subscription' })}
                </h2>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    statusTone === 'ok'
                      ? 'bg-emerald-50 text-emerald-700'
                      : statusTone === 'warn'
                        ? 'bg-amber-50 text-amber-800'
                        : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {subStatus
                    ? t(`app.organization.subscription.status.${String(subStatus).toLowerCase()}`, {
                        defaultValue: String(subStatus),
                      })
                    : canLoadBilling
                      ? t('app.organization.subscription.status.unknown', { defaultValue: 'Unknown' })
                      : t('app.organization.subscription.status.restricted', { defaultValue: 'Restricted' })}
                </span>
              </div>
              {canLoadBilling && billing ? (
                <dl className="space-y-2 text-sm">
                  <Row
                    label={t('app.organization.subscription.plan', { defaultValue: 'Plan' })}
                    value={planLabel(billing)}
                  />
                  <Row
                    label={t('app.organization.subscription.period', { defaultValue: 'Period' })}
                    value={formatPeriod(
                      billing.subscription?.current_period_start,
                      billing.subscription?.current_period_end,
                      dateLocale,
                    )}
                  />
                  <Row
                    label={t('app.organization.subscription.slots', { defaultValue: 'Company slots' })}
                    value={slots?.unlimited ? '∞' : `${usedSlots} / ${limitSlots || '—'}`}
                  />
                  <Row
                    label={t('app.organization.subscription.available', { defaultValue: 'Available' })}
                    value={slots?.unlimited ? '∞' : String(availableSlots ?? '—')}
                  />
                  <div className="flex items-center justify-between gap-3">
                    <dt className="text-slate-500">
                      {t('app.organization.subscription.payment', { defaultValue: 'Payment' })}
                    </dt>
                    <dd>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          paymentPaid ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {paymentPaid
                          ? t('app.organization.subscription.paid', { defaultValue: 'Paid' })
                          : t('app.organization.subscription.unpaid', { defaultValue: 'Check billing' })}
                      </span>
                    </dd>
                  </div>
                </dl>
              ) : (
                <p className="text-sm text-slate-500">
                  {t('app.organization.subscription.no_access', {
                    defaultValue: 'Billing details are available to administrators.',
                  })}
                </p>
              )}
              <div className="mt-auto pt-2">
                <Link className="btn-secondary w-full justify-center" to={CRM_APP_PATHS.settingsBilling}>
                  {t('app.organization.subscription.manage', { defaultValue: 'Manage subscription' })}
                </Link>
              </div>
            </section>

            {/* Operations / slots donut */}
            <section className="app-surface flex flex-col space-y-3 p-5">
              <h2 className="text-base font-semibold text-slate-900">
                {t('app.organization.operations.title', { defaultValue: 'Company slots' })}
              </h2>
              {slots?.unlimited ? (
                <p className="py-8 text-center text-sm text-slate-500">
                  {t('app.organization.operations.unlimited', { defaultValue: 'Unlimited company slots on this plan.' })}
                </p>
              ) : (
                <>
                  <div className="relative">
                    <Donut used={usedSlots} total={limitSlots || usedSlots || 1} />
                    <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                      <div className="px-3 text-center">
                        <p className="text-lg font-semibold text-slate-900">
                          {usedSlots} / {limitSlots || '—'}
                        </p>
                        <p className="text-xs text-slate-500">
                          {t('app.organization.operations.used_label', { defaultValue: 'slots used' })}
                        </p>
                      </div>
                    </div>
                  </div>
                  <ul className="space-y-1 text-sm text-slate-600">
                    <li className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-brand-600" />
                      {t('app.organization.operations.used', {
                        defaultValue: 'Used: {count}',
                        values: { count: usedSlots },
                      })}
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-slate-300" />
                      {t('app.organization.operations.available', {
                        defaultValue: 'Available: {count}',
                        values: { count: availableSlots ?? '—' },
                      })}
                    </li>
                  </ul>
                </>
              )}
              <div className="mt-auto pt-2">
                <Link
                  className="btn-secondary w-full justify-center"
                  to={`${CRM_APP_PATHS.settingsBilling}?focus=company-slots`}
                >
                  {t('app.organization.operations.details', { defaultValue: 'Slot details' })}
                </Link>
              </div>
            </section>

            {/* Modules */}
            <section className="app-surface space-y-3 p-5">
              <div>
                <h2 className="text-base font-semibold text-slate-900">
                  {t('app.organization.modules.title', { defaultValue: 'Modules' })}
                </h2>
                <p className="text-sm text-slate-500">
                  {t('app.organization.modules.subtitle', {
                    defaultValue: 'Modules enabled for this workspace.',
                  })}
                </p>
              </div>
              {enabledModules.length ? (
                <div className="flex flex-wrap gap-2">
                  {enabledModules.map((key) => (
                    <span
                      key={key}
                      className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700"
                    >
                      {t(`app.platform.tenants.modules.items.${key}`, { defaultValue: key })}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">
                  {t('app.organization.modules.empty', { defaultValue: 'Module list unavailable.' })}
                </p>
              )}
              <Link className="inline-flex text-sm font-medium text-brand-700 hover:text-brand-800" to={CRM_APP_PATHS.settingsUsers}>
                {t('app.organization.modules.all', { defaultValue: 'All modules' })} →
              </Link>
            </section>

            {/* Companies */}
            <section className="app-surface space-y-3 p-5">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    {t('app.organization.companies.title', { defaultValue: 'Companies' })}
                  </h2>
                  <p className="text-sm text-slate-500">
                    {t('app.organization.companies.subtitle', {
                      defaultValue: 'Operating company profiles in this workspace.',
                    })}
                  </p>
                </div>
                <IconBuilding className="text-slate-400" size={20} stroke={1.75} />
              </div>
              {companies.length ? (
                <ul className="divide-y divide-slate-100">
                  {companies.slice(0, 5).map((company) => (
                    <li key={company.id}>
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-2 py-2.5 text-left text-sm hover:text-brand-700"
                        onClick={() => {
                          void (async () => {
                            try {
                              await setActiveOwnCompany(company.id)
                            } catch {
                              // best-effort
                            }
                            navigate(CRM_APP_PATHS.myCompany)
                          })()
                        }}
                      >
                        <span className="truncate font-medium text-slate-900">{company.name || company.legal_name || company.id}</span>
                        <IconChevronRight size={16} className="shrink-0 text-slate-400" />
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500">
                  {t('app.organization.companies.empty', { defaultValue: 'No operating companies yet.' })}
                </p>
              )}
              <div className="flex flex-wrap gap-2 pt-1">
                <Link className="btn-secondary btn-sm" to={CRM_APP_PATHS.myCompany}>
                  {t('app.organization.companies.open_profile', { defaultValue: 'Open company profile' })}
                </Link>
                <Link className="btn-primary btn-sm" to={CRM_APP_PATHS.onboardingCompany}>
                  {t('app.organization.companies.create', { defaultValue: 'Create company' })}
                </Link>
              </div>
            </section>

            {/* Users */}
            <section className="app-surface flex flex-col space-y-3 p-5">
              <div>
                <h2 className="text-base font-semibold text-slate-900">
                  {t('app.organization.users.title', { defaultValue: 'Users' })}
                </h2>
                <p className="text-sm text-slate-500">
                  {t('app.organization.users.subtitle', { defaultValue: 'Active users in this workspace.' })}
                </p>
              </div>
              {avatarMembers.length ? (
                <div className="flex items-center">
                  {avatarMembers.map((member, index) => (
                    <MemberAvatar key={member.user_id || member.email || index} member={member} index={index} />
                  ))}
                  {extraMembers > 0 ? (
                    <span className="relative z-0 -ml-2 flex h-10 w-10 items-center justify-center rounded-full border-2 border-white bg-slate-100 text-xs font-semibold text-slate-600">
                      +{extraMembers}
                    </span>
                  ) : null}
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <IconUsers size={18} />
                  {t('app.organization.users.empty', { defaultValue: 'User list unavailable.' })}
                </div>
              )}
              <div className="mt-auto pt-2">
                <Link className="btn-secondary w-full justify-center" to={CRM_APP_PATHS.settingsUsers}>
                  {t('app.organization.users.manage', { defaultValue: 'Manage users' })} →
                </Link>
              </div>
            </section>

            {/* Billing docs */}
            <section className="app-surface space-y-3 p-5 xl:col-span-2">
              <div>
                <h2 className="text-base font-semibold text-slate-900">
                  {t('app.organization.billing_docs.title', { defaultValue: 'Billing & documents' })}
                </h2>
                <p className="text-sm text-slate-500">
                  {t('app.organization.billing_docs.subtitle', {
                    defaultValue: 'Payments and closing documents for this workspace.',
                  })}
                </p>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <Link
                  to={CRM_APP_PATHS.settingsBilling}
                  className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/70 px-4 py-3 text-sm font-medium text-slate-800 hover:bg-slate-50"
                >
                  <span className="inline-flex items-center gap-2">
                    <IconCreditCard size={18} className="text-brand-700" />
                    {t('app.organization.billing_docs.history', { defaultValue: 'Payment history' })}
                  </span>
                  <IconChevronRight size={16} className="text-slate-400" />
                </Link>
                <Link
                  to={CRM_APP_PATHS.invoices}
                  className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/70 px-4 py-3 text-sm font-medium text-slate-800 hover:bg-slate-50"
                >
                  <span className="inline-flex items-center gap-2">
                    <IconFileText size={18} className="text-brand-700" />
                    {t('app.organization.billing_docs.closing', { defaultValue: 'Closing documents' })}
                  </span>
                  <IconChevronRight size={16} className="text-slate-400" />
                </Link>
              </div>
            </section>
          </div>
        )}
      </div>
    </PageShell>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-900">{value}</dd>
    </div>
  )
}

function MemberAvatar({ member, index }: { member: AdminUser; index: number }) {
  const label = member.full_name || member.email || '?'
  return (
    <span
      title={label}
      className="relative flex h-10 w-10 items-center justify-center rounded-full border-2 border-white bg-brand-100 text-xs font-semibold text-brand-800"
      style={{ zIndex: 10 - index, marginLeft: index === 0 ? 0 : -8 }}
    >
      {initials(label)}
    </span>
  )
}
