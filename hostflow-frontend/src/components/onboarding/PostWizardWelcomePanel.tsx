import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  IconCheck,
  IconRocket,
  IconSparkles,
  IconX,
  IconArrowRight,
} from '@tabler/icons-react'

import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  completeReminder,
  getOnboardingWizard,
  getOnboardingWizardFirstLead,
  type OnboardingWizardFirstLead,
  type OnboardingWizardState,
} from '../../api/client'

const DISMISS_KEY = 'hf:wizard-welcome:dismissed'
const VISIBLE_DAYS_AFTER_FINISH = 7
const DAY_MS = 24 * 60 * 60 * 1000

function readDismissed(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return window.localStorage.getItem(DISMISS_KEY) === '1'
  } catch {
    return false
  }
}

function persistDismissed(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(DISMISS_KEY, '1')
  } catch {
    // ignore
  }
}

/**
 * Phase 2 #3 — first 7 days after wizard completion the dashboard greets
 * the user with a focused panel showing «your first lead + its next-best-action»
 * + 4 deep-links into the core surfaces (Pipeline / Documents / Tasks / Inbox).
 *
 * Visibility rules:
 * - wizard.finished === true AND wizard.completed_at ≤ 7 days ago, OR
 *   the URL carries `?welcome=1` (the secondary CTA on `OnboardingCompanyPage`).
 * - Once user clicks ✕ — never reappears for this browser
 *   (`hf:wizard-welcome:dismissed` in localStorage). Wizard rail keeps reminding.
 *
 * Strictly non-blocking: above the dashboard but does not displace any widget.
 */
export function PostWizardWelcomePanel() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const location = useLocation()
  const [wizard, setWizard] = useState<OnboardingWizardState | null>(null)
  const [snapshot, setSnapshot] = useState<OnboardingWizardFirstLead | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [dismissed, setDismissed] = useState<boolean>(() => readDismissed())
  const [completing, setCompleting] = useState(false)
  const [completed, setCompleted] = useState(false)

  const forceShowFromUrl = useMemo(() => {
    const params = new URLSearchParams(location.search)
    return params.get('welcome') === '1'
  }, [location.search])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const [w, s] = await Promise.all([
          getOnboardingWizard().catch(() => null),
          getOnboardingWizardFirstLead().catch(() => null),
        ])
        if (cancelled) return
        setWizard(w)
        setSnapshot(s)
      } finally {
        if (!cancelled) setLoaded(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const showPanel = useMemo(() => {
    if (!loaded) return false
    if (dismissed) return false
    if (forceShowFromUrl) return true
    if (!wizard?.finished) return false
    const finishedAt = wizard.completed_at ? Date.parse(wizard.completed_at) : NaN
    if (!Number.isFinite(finishedAt)) return true
    return Date.now() - finishedAt <= VISIBLE_DAYS_AFTER_FINISH * DAY_MS
  }, [loaded, dismissed, forceShowFromUrl, wizard])

  const onDismiss = useCallback(() => {
    persistDismissed()
    setDismissed(true)
    if (forceShowFromUrl) {
      const params = new URLSearchParams(location.search)
      params.delete('welcome')
      const search = params.toString()
      navigate(
        { pathname: location.pathname, search: search ? `?${search}` : '', hash: location.hash },
        { replace: true },
      )
    }
  }, [forceShowFromUrl, location.search, location.pathname, location.hash, navigate])

  const onCompleteNba = useCallback(async () => {
    if (!snapshot?.nba_id) return
    setCompleting(true)
    try {
      await completeReminder(snapshot.nba_id)
      setCompleted(true)
    } catch {
      // best-effort: keep panel open so the user can retry from the lead card
    } finally {
      setCompleting(false)
    }
  }, [snapshot?.nba_id])

  if (!showPanel) return null

  const dueLabel = (() => {
    if (!snapshot?.nba_due_at) return null
    const dt = new Date(snapshot.nba_due_at)
    if (Number.isNaN(dt.getTime())) return null
    return dt.toLocaleString()
  })()

  const tourLinks: Array<{ to: string; labelKey: string; defaultLabel: string }> = [
    {
      to: CRM_APP_PATHS.pipeline,
      labelKey: 'app.dashboard.welcome.tour.pipeline',
      defaultLabel: 'Open pipeline',
    },
    {
      to: CRM_APP_PATHS.documents,
      labelKey: 'app.dashboard.welcome.tour.documents',
      defaultLabel: 'Documents',
    },
    {
      to: CRM_APP_PATHS.tasks,
      labelKey: 'app.dashboard.welcome.tour.tasks',
      defaultLabel: 'Tasks & SLA',
    },
    {
      to: CRM_APP_PATHS.inbox,
      labelKey: 'app.dashboard.welcome.tour.inbox',
      defaultLabel: 'Inbox',
    },
  ]

  return (
    <section
      role="region"
      aria-label={t('app.dashboard.welcome.aria_label', {
        defaultValue: 'Welcome — getting started with your workspace',
      })}
      className="mb-3 overflow-hidden rounded-2xl border border-brand-200 bg-gradient-to-br from-brand-50 via-white to-emerald-50 shadow-sm"
    >
      <div className="flex items-start gap-3 p-4 sm:p-5">
        <span
          aria-hidden
          className="hidden h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700 sm:inline-flex"
        >
          <IconRocket size={18} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-slate-900 sm:text-lg">
                {t('app.dashboard.welcome.title', {
                  defaultValue: 'Welcome to HostFlow — your workspace is ready',
                })}
              </h2>
              <p className="mt-0.5 text-xs text-slate-600 sm:text-sm">
                {t('app.dashboard.welcome.subtitle', {
                  defaultValue:
                    'Here’s the first lead waiting for you and a tour of where to go next.',
                })}
              </p>
            </div>
            <button
              type="button"
              onClick={onDismiss}
              className="shrink-0 rounded-md p-1 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
              aria-label={t('app.dashboard.welcome.dismiss', { defaultValue: 'Dismiss' })}
              title={t('app.dashboard.welcome.dismiss', { defaultValue: 'Dismiss' })}
            >
              <IconX size={16} aria-hidden />
            </button>
          </div>

          {snapshot?.has_lead ? (
            <div className="mt-3 rounded-xl border border-slate-200 bg-white p-3 sm:p-4">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-brand-700">
                <IconSparkles size={12} aria-hidden />
                {t('app.dashboard.welcome.first_lead_kicker', {
                  defaultValue: 'Your first lead',
                })}
                {snapshot.is_demo ? (
                  <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800">
                    {t('app.dashboard.welcome.demo_badge', { defaultValue: 'Demo' })}
                  </span>
                ) : null}
              </div>
              <div className="mt-1 truncate text-sm font-semibold text-slate-900">
                {snapshot.title ?? t('app.dashboard.welcome.lead_unknown', { defaultValue: 'Lead' })}
              </div>
              {snapshot.nba_title ? (
                <p className="mt-1 text-xs text-slate-600 sm:text-sm">
                  <span className="font-medium text-slate-700">
                    {t('app.dashboard.welcome.nba_label', { defaultValue: 'Next best action:' })}
                  </span>{' '}
                  {snapshot.nba_title}
                  {dueLabel ? (
                    <span className="text-slate-500"> · {dueLabel}</span>
                  ) : null}
                </p>
              ) : (
                <p className="mt-1 text-xs text-slate-500">
                  {t('app.dashboard.welcome.nba_none', {
                    defaultValue: 'No reminder yet — open the lead and plan your first follow-up.',
                  })}
                </p>
              )}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Link
                  to={snapshot.leads_url}
                  className="inline-flex items-center gap-1.5 rounded-md bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-brand-700"
                >
                  {t('app.dashboard.welcome.open_lead', { defaultValue: 'Open lead' })}
                  <IconArrowRight size={14} stroke={1.9} aria-hidden />
                </Link>
                {snapshot.nba_id ? (
                  <button
                    type="button"
                    onClick={() => void onCompleteNba()}
                    disabled={completing || completed}
                    className="inline-flex items-center gap-1.5 rounded-md border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800 transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <IconCheck size={14} stroke={1.9} aria-hidden />
                    {completed
                      ? t('app.dashboard.welcome.nba_done', { defaultValue: 'NBA completed' })
                      : completing
                        ? t('common.saving')
                        : t('app.dashboard.welcome.nba_complete', {
                            defaultValue: 'Mark NBA done',
                          })}
                  </button>
                ) : null}
                <Link
                  to={CRM_APP_PATHS.tasks}
                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  {t('app.dashboard.welcome.add_followup', { defaultValue: 'Add follow-up' })}
                </Link>
              </div>
            </div>
          ) : (
            <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50/60 p-3 text-xs text-amber-900 sm:text-sm">
              {t('app.dashboard.welcome.no_lead_yet', {
                defaultValue:
                  'No leads yet — open Leads to add one manually, or finish connecting your channel from the setup wizard.',
              })}
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Link
                  to={CRM_APP_PATHS.leads}
                  className="inline-flex items-center gap-1.5 rounded-md bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-amber-700"
                >
                  {t('app.dashboard.welcome.open_leads', { defaultValue: 'Open Leads' })}
                </Link>
                <Link
                  to={CRM_APP_PATHS.onboardingWizard}
                  className="inline-flex items-center gap-1.5 rounded-md border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-50"
                >
                  {t('app.dashboard.welcome.resume_wizard', { defaultValue: 'Resume setup' })}
                </Link>
              </div>
            </div>
          )}

          <div className="mt-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              {t('app.dashboard.welcome.tour_kicker', { defaultValue: 'Where to go next' })}
            </p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {tourLinks.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:border-brand-300 hover:text-brand-700"
                >
                  {t(item.labelKey, { defaultValue: item.defaultLabel })}
                  <IconArrowRight size={12} stroke={1.9} aria-hidden />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default PostWizardWelcomePanel
