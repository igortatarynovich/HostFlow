import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { Modal } from '../components/Modal'
import { CRM_APP_PATHS } from '../app/crmAppPaths.generated'
import { useI18n } from '../i18n'
import { isPlanLimitOrBillingGateError } from '../utils/friendlyError'

export type PlanLimitModalContextValue = {
  /** Opens the plan-limit modal when `err` is a quota / billing gate; returns whether it handled the error. */
  showPlanLimitIfNeeded: (err: unknown, fallbackTitle: string) => boolean
}

const PlanLimitModalContext = createContext<PlanLimitModalContextValue | null>(null)

type PlanTier = 'starter' | 'team' | 'pro' | 'enterprise'
type PlanLimitModalInfo = {
  requiredPlanLabel: string
  currentPlanLabel: string
  detail?: string
}

function normalizePlan(value: unknown): PlanTier | null {
  const plan = String(value ?? '')
    .trim()
    .toLowerCase()
  if (plan === 'starter' || plan === 'team' || plan === 'pro' || plan === 'enterprise') return plan
  return null
}

function planLabel(t: (key: string, options?: any) => string, plan: PlanTier | null, fallbackKey: string): string {
  if (!plan) {
    return t(fallbackKey, {
      defaultValue: fallbackKey.endsWith('required_plan_fallback') ? 'a higher' : 'your current',
    })
  }
  const key = `app.billing.plan_limit.plan_name.${plan}`
  const translated = t(key, { defaultValue: plan })
  return translated === key ? plan : translated
}

function resolveModalInfo(err: any, t: (key: string, options?: any) => string): PlanLimitModalInfo {
  const detailPayload = err?.response?.data?.detail
  const detailMessage =
    typeof detailPayload === 'object' &&
    detailPayload &&
    typeof detailPayload.message === 'string' &&
    detailPayload.message.trim()
      ? detailPayload.message.trim()
      : typeof detailPayload === 'string' && detailPayload.trim()
        ? detailPayload.trim()
        : undefined
  const code =
    typeof detailPayload === 'object' && detailPayload && typeof detailPayload.code === 'string'
      ? String(detailPayload.code).trim().toUpperCase()
      : ''
  const requiredPlanRaw =
    typeof detailPayload === 'object' && detailPayload
      ? detailPayload.required_plan ?? detailPayload.plan ?? detailPayload.minimum_plan
      : null
  const currentPlanRaw =
    typeof detailPayload === 'object' && detailPayload
      ? detailPayload.current_plan ?? detailPayload.current_plan_code ?? detailPayload.plan_code
      : null
  const requiredPlanFromCode: PlanTier | null = code === 'PLAN_REQUIRES_TEAM' ? 'team' : null
  const requiredPlan = normalizePlan(requiredPlanRaw) ?? requiredPlanFromCode
  const currentPlan = normalizePlan(currentPlanRaw)
  return {
    requiredPlanLabel: planLabel(t, requiredPlan, 'app.billing.plan_limit.required_plan_fallback'),
    currentPlanLabel: planLabel(t, currentPlan, 'app.billing.plan_limit.current_plan_fallback'),
    detail: detailMessage,
  }
}

export function usePlanLimitModal(): PlanLimitModalContextValue | null {
  return useContext(PlanLimitModalContext)
}

export function PlanLimitModalProvider({ children }: { children: ReactNode }) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [info, setInfo] = useState<PlanLimitModalInfo | null>(null)

  const showPlanLimitIfNeeded = useCallback(
    (err: unknown, fallbackTitle: string): boolean => {
      if (!isPlanLimitOrBillingGateError(err)) return false
      void fallbackTitle
      setInfo(resolveModalInfo(err, t))
      return true
    },
    [t],
  )

  const close = useCallback(() => setInfo(null), [])

  const onUpgrade = useCallback(() => {
    close()
    navigate(CRM_APP_PATHS.settingsBillingPlan)
  }, [close, navigate])

  const onTalkToSales = useCallback(() => {
    close()
    if (typeof window === 'undefined') return
    window.location.href = 'mailto:sales@hostflow.app'
  }, [close])

  const value = useMemo(() => ({ showPlanLimitIfNeeded }), [showPlanLimitIfNeeded])

  return (
    <PlanLimitModalContext.Provider value={value}>
      {children}
      <Modal open={Boolean(info)} onClose={close} title={t('app.billing.plan_limit.title', { defaultValue: 'Plan limit reached' })}>
        {info ? (
          <div className="space-y-4 text-sm text-slate-700">
            <p>
              {t('app.billing.plan_limit.body', {
                defaultValue: 'This action requires the {required} plan. Your current plan is {current}.',
                values: { required: info.requiredPlanLabel, current: info.currentPlanLabel },
              })}
            </p>
            {info.detail ? <p className="whitespace-pre-wrap text-xs text-slate-500">{info.detail}</p> : null}
            <div className="flex flex-wrap gap-2 pt-2">
              <button type="button" className="btn-primary" onClick={onUpgrade}>
                {t('app.billing.plan_limit.actions.upgrade', { defaultValue: 'Upgrade plan' })}
              </button>
              <button type="button" className="btn-secondary" onClick={onTalkToSales}>
                {t('app.billing.plan_limit.actions.talk_to_sales', { defaultValue: 'Talk to sales' })}
              </button>
            </div>
          </div>
        ) : null}
      </Modal>
    </PlanLimitModalContext.Provider>
  )
}
