import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconRocket, IconX } from '@tabler/icons-react'

import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  getOnboardingWizard,
  type OnboardingWizardState,
  type OnboardingWizardStepKey,
} from '../../api/client'

const DISMISS_KEY = 'hf:wizard-rail:dismissed-until'
const VISIBLE_DAYS_AFTER_START = 7
const DAY_MS = 24 * 60 * 60 * 1000

const STEP_ORDER: OnboardingWizardStepKey[] = ['type', 'client', 'vacancy', 'channel', 'first_lead']

function readDismissedUntil(): number {
  if (typeof window === 'undefined') return 0
  try {
    const raw = window.localStorage.getItem(DISMISS_KEY)
    const ms = raw ? Number.parseInt(raw, 10) : 0
    return Number.isFinite(ms) ? ms : 0
  } catch {
    return 0
  }
}

function persistDismissedUntil(ms: number): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(DISMISS_KEY, String(ms))
  } catch {
    // ignore
  }
}

export type WizardSetupRailProps = {
  /** Hide rail entirely (e.g. on onboarding pages, or until tenant is ready). */
  hidden?: boolean
}

/**
 * Persistent (but dismissible) ambient rail that reminds the user to finish
 * the 5-step onboarding wizard. Visible until the wizard is `finished` or
 * 7 days after `started_at` — whichever comes first. Per Phase 2 acceptance
 * (HOSTFLOW_AUDIT_AND_PLAN.md): no blocking UI, dismissible per day.
 */
export function WizardSetupRail({ hidden }: WizardSetupRailProps) {
  const { t } = useI18n()
  const [wizard, setWizard] = useState<OnboardingWizardState | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [dismissedUntil, setDismissedUntil] = useState<number>(() => readDismissedUntil())

  useEffect(() => {
    if (hidden) return
    let cancelled = false
    void (async () => {
      try {
        const data = await getOnboardingWizard()
        if (!cancelled) setWizard(data)
      } catch {
        if (!cancelled) setWizard(null)
      } finally {
        if (!cancelled) setLoaded(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [hidden])

  const showRail = useMemo(() => {
    if (hidden || !loaded || !wizard) return false
    if (wizard.finished) return false
    const startedMs = wizard.started_at ? Date.parse(wizard.started_at) : Date.now()
    if (Number.isFinite(startedMs)) {
      const ageMs = Date.now() - startedMs
      if (ageMs > VISIBLE_DAYS_AFTER_START * DAY_MS) return false
    }
    if (dismissedUntil && dismissedUntil > Date.now()) return false
    return true
  }, [hidden, loaded, wizard, dismissedUntil])

  const completed = wizard?.completed_steps?.length ?? 0
  const total = STEP_ORDER.length
  const pctRaw = total > 0 ? (completed / total) * 100 : 0
  const pct = Math.min(100, Math.max(0, Math.round(pctRaw)))
  const remaining = Math.max(0, total - completed)

  const onDismiss = useCallback(() => {
    const until = Date.now() + DAY_MS
    persistDismissedUntil(until)
    setDismissedUntil(until)
  }, [])

  if (!showRail || !wizard) return null

  return (
    <div
      role="region"
      aria-label={t('app.onboarding.wizard.rail.aria_label', {
        defaultValue: 'Onboarding setup progress',
      })}
      className="border-b border-brand-200 bg-brand-50/80"
    >
      <div className="mx-auto flex w-full max-w-7xl items-center gap-3 px-4 py-2">
        <span
          aria-hidden
          className="hidden h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700 sm:inline-flex"
        >
          <IconRocket size={14} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-3">
            <p className="truncate text-xs font-medium text-brand-900 sm:text-sm">
              {t('app.onboarding.wizard.rail.title', {
                defaultValue: 'Finish setup — {n} step(s) left to your first lead with NBA',
                values: { n: remaining },
              })}
            </p>
            <span className="hidden text-xs font-semibold text-brand-700 sm:inline">
              {completed}/{total}
            </span>
          </div>
          <div
            className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-brand-100"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={pct}
          >
            <div
              className="h-full rounded-full bg-brand-600 transition-[width] duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
        <Link
          to={CRM_APP_PATHS.onboardingWizard}
          className="hidden shrink-0 rounded-md bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-brand-700 sm:inline-flex"
        >
          {t('app.onboarding.wizard.rail.resume', { defaultValue: 'Resume setup' })}
        </Link>
        <Link
          to={CRM_APP_PATHS.onboardingWizard}
          className="shrink-0 rounded-md bg-brand-600 px-2.5 py-1.5 text-xs font-semibold text-white shadow-sm sm:hidden"
          aria-label={t('app.onboarding.wizard.rail.resume', { defaultValue: 'Resume setup' })}
        >
          →
        </Link>
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded-md p-1 text-brand-700/70 transition hover:bg-brand-100 hover:text-brand-900"
          aria-label={t('app.onboarding.wizard.rail.dismiss', {
            defaultValue: 'Hide for today',
          })}
          title={t('app.onboarding.wizard.rail.dismiss_title', {
            defaultValue: 'Hide for today',
          })}
        >
          <IconX size={14} aria-hidden />
        </button>
      </div>
    </div>
  )
}

export default WizardSetupRail
