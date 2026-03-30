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
import type { FriendlyErrorInfo } from '../utils/friendlyError'
import { getFriendlyErrorInfo, isPlanLimitOrBillingGateError } from '../utils/friendlyError'

export type PlanLimitModalContextValue = {
  /** Opens the plan-limit modal when `err` is a quota / billing gate; returns whether it handled the error. */
  showPlanLimitIfNeeded: (err: unknown, fallbackTitle: string) => boolean
}

const PlanLimitModalContext = createContext<PlanLimitModalContextValue | null>(null)

export function usePlanLimitModal(): PlanLimitModalContextValue | null {
  return useContext(PlanLimitModalContext)
}

export function PlanLimitModalProvider({ children }: { children: ReactNode }) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [info, setInfo] = useState<FriendlyErrorInfo | null>(null)

  const showPlanLimitIfNeeded = useCallback(
    (err: unknown, fallbackTitle: string): boolean => {
      if (!isPlanLimitOrBillingGateError(err)) return false
      setInfo(getFriendlyErrorInfo(err, fallbackTitle, t))
      return true
    },
    [t],
  )

  const close = useCallback(() => setInfo(null), [])

  const onBilling = useCallback(() => {
    close()
    navigate(CRM_APP_PATHS.settingsBilling)
  }, [close, navigate])

  const value = useMemo(() => ({ showPlanLimitIfNeeded }), [showPlanLimitIfNeeded])

  return (
    <PlanLimitModalContext.Provider value={value}>
      {children}
      <Modal open={Boolean(info)} onClose={close} title={info?.title}>
        {info ? (
          <div className="space-y-4 text-sm text-slate-700">
            {info.detail ? <p className="whitespace-pre-wrap">{info.detail}</p> : null}
            <p>{info.hint}</p>
            {info.secondaryTo ? (
              <div className="flex flex-wrap gap-2 pt-2">
                <button type="button" className="btn-primary" onClick={onBilling}>
                  {info.secondaryLabel ?? t('app.api_errors.open_billing')}
                </button>
                <button type="button" className="btn-secondary" onClick={close}>
                  {t('common.actions.close', { defaultValue: 'Close' })}
                </button>
              </div>
            ) : (
              <button type="button" className="btn-primary mt-2" onClick={close}>
                {t('common.actions.close', { defaultValue: 'Close' })}
              </button>
            )}
          </div>
        ) : null}
      </Modal>
    </PlanLimitModalContext.Provider>
  )
}
