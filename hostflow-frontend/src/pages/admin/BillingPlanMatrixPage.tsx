import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowUpRight, IconCheck, IconLoader2, IconMail } from '@tabler/icons-react'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  createBillingCheckoutSession,
  getBillingPlanMatrix,
  type BillingPlanCode,
  type BillingPlanMatrix,
} from '../../api/billing'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

function normalizePlanCode(code: string | null | undefined): BillingPlanCode {
  const normalized = (code || '').trim().toLowerCase()
  if (normalized === 'team' || normalized === 'pro' || normalized === 'enterprise') return normalized
  return 'starter'
}

function formatValue(v: number | boolean | string | null): string {
  if (v == null) return '-'
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  return String(v)
}

export default function BillingPlanMatrixPage() {
  const [matrix, setMatrix] = useState<BillingPlanMatrix | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [checkoutLoadingCode, setCheckoutLoadingCode] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getBillingPlanMatrix()
      setMatrix(data)
    } catch (e) {
      setError(getFriendlyErrorInfo(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const currentPlanCode = useMemo(() => normalizePlanCode(matrix?.current_plan_code), [matrix?.current_plan_code])

  const onUpgrade = useCallback(async (planCode: BillingPlanCode) => {
    if (planCode === 'enterprise') return
    setCheckoutLoadingCode(planCode)
    try {
      const session = await createBillingCheckoutSession({
        plan_code: planCode,
        success_url: `${window.location.origin}${CRM_APP_PATHS.settingsBilling}?checkout=success`,
        cancel_url: `${window.location.origin}${CRM_APP_PATHS.settingsBillingPlan}`,
      })
      window.location.assign(session.checkout_url)
    } catch (e) {
      setError(getFriendlyErrorInfo(e))
    } finally {
      setCheckoutLoadingCode(null)
    }
  }, [])

  return (
    <section className="space-y-6">
      <SettingsSubpageHeader
        title="Plan comparison"
        subtitle="What you have now and what you get on upgrade."
        actions={(
          <Link className="btn-secondary inline-flex items-center gap-2" to={CRM_APP_PATHS.settingsBilling}>
            Back to billing
          </Link>
        )}
      />

      {error ? <ErrorRecoveryBanner error={error} onRetry={() => void load()} /> : null}

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Feature</th>
              {(matrix?.plans || []).map((plan) => {
                const code = normalizePlanCode(plan.code)
                const isCurrent = currentPlanCode === code
                return (
                  <th key={plan.code} className="px-4 py-3 text-left font-semibold text-slate-700">
                    <div className="flex items-center gap-2">
                      <span>{plan.name}</span>
                      {isCurrent ? (
                        <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                          <IconCheck size={12} className="mr-1" />
                          You have now
                        </span>
                      ) : null}
                    </div>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  Loading plan matrix...
                </td>
              </tr>
            ) : (
              (matrix?.features || []).map((feature) => (
                <tr key={feature.key} className="border-t border-slate-100">
                  <td className="px-4 py-3 font-medium text-slate-800">{feature.label}</td>
                  {(matrix?.plans || []).map((plan) => {
                    const planCode = normalizePlanCode(plan.code)
                    const currentValue = feature.values[planCode]
                    const current = formatValue(currentValue as number | boolean | string | null)
                    const isIncluded = Boolean(currentValue)
                    const isCurrent = currentPlanCode === planCode
                    return (
                      <td key={`${feature.key}-${planCode}`} className="px-4 py-3 text-slate-700">
                        <div className="flex items-center justify-between gap-2">
                          <span>{current}</span>
                          {!isCurrent && !isIncluded ? (
                            feature.upgrade_checkout_allowed && planCode !== 'enterprise' ? (
                              <button
                                type="button"
                                className="btn-primary btn-xs inline-flex items-center gap-1"
                                onClick={() => void onUpgrade(planCode)}
                                disabled={checkoutLoadingCode === planCode}
                              >
                                {checkoutLoadingCode === planCode ? <IconLoader2 size={14} className="animate-spin" /> : null}
                                Upgrade
                                <IconArrowUpRight size={14} />
                              </button>
                            ) : (
                              <a
                                href="mailto:sales@hostflow.app"
                                className="btn-secondary btn-xs inline-flex items-center gap-1"
                              >
                                Talk to sales
                                <IconMail size={14} />
                              </a>
                            )
                          ) : null}
                        </div>
                      </td>
                    )
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
