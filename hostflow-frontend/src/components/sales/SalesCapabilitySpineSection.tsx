import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import {
  getSalesInquiryCapabilitySpine,
  type SalesCapabilitySpine,
} from '../../api/applications'
import { clientDetailPath } from '../../services/platformHandoff'
import { useI18n } from '../../i18n'

type Props = {
  applicationId: string
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-100 py-1.5 last:border-0">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-800">{value}</dd>
    </div>
  )
}

/** Display-only Pipeline v1 spine — no domain decisions in the UI. */
export default function SalesCapabilitySpineSection({ applicationId }: Props) {
  const { t } = useI18n()
  const [spine, setSpine] = useState<SalesCapabilitySpine | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)
    void getSalesInquiryCapabilitySpine(applicationId)
      .then((data) => {
        if (!mounted) return
        setSpine(data)
      })
      .catch((err: unknown) => {
        if (!mounted) return
        const detail =
          (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
          (err as Error)?.message ??
          t('app.sales_inquiry.capability_spine_load_failed', {
            defaultValue: 'Не удалось загрузить статус Pipeline',
          })
        setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
        setSpine(null)
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [applicationId, t])

  if (loading) {
    return (
      <p className="text-sm text-slate-500" data-testid="sales-capability-spine-loading">
        {t('common.loading', { defaultValue: 'Ładowanie…' })}
      </p>
    )
  }

  if (error) {
    return (
      <div
        className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
        data-testid="sales-capability-spine-error"
      >
        {error}
      </div>
    )
  }

  if (!spine) return null

  const capLabel = spine.capability.code
    ? spine.capability.code
    : t('app.sales_inquiry.capability_undecided', { defaultValue: 'Не задана (контракт)' })
  const reviewStatus =
    spine.review.status ||
    t('app.sales_inquiry.review_absent', { defaultValue: 'нет записи review' })
  const convertLabel = spine.convert.available
    ? t('app.sales_inquiry.convert_available', { defaultValue: 'Доступен (домен)' })
    : spine.convert.reason ||
      t('app.sales_inquiry.convert_unavailable', { defaultValue: 'Недоступен' })
  const clientId = spine.convert.client_account_id || spine.traceability.lineage?.client_account_id
  const clientHref = clientId ? clientDetailPath(clientId) : undefined

  return (
    <section
      className="rounded-lg border border-slate-200 bg-white px-3 py-3"
      data-testid="sales-capability-spine"
    >
      <h3 className="text-sm font-semibold text-slate-900">
        {t('app.sales_inquiry.capability_spine_title', { defaultValue: 'Sales Pipeline' })}
      </h3>
      <p className="mt-0.5 text-xs text-slate-500">
        {t('app.sales_inquiry.capability_spine_hint', {
          defaultValue: 'Только отображение. Решения принимает домен, не этот экран.',
        })}
      </p>
      {spine.missing_sales_inquiry ? (
        <p className="mt-2 text-sm text-amber-800">
          {t('app.sales_inquiry.missing_sales_inquiry', {
            defaultValue: 'SalesInquiry ещё не создан для этого транспорта.',
          })}
        </p>
      ) : null}
      <dl className="mt-2">
        <Row
          label={t('app.sales_inquiry.capability_label', { defaultValue: 'Capability' })}
          value={
            <span>
              {capLabel}
              {!spine.capability.decided ? (
                <span className="ml-1 text-xs text-slate-400">
                  ({t('app.sales_inquiry.capability_proxy', { defaultValue: 'proxy' })})
                </span>
              ) : null}
            </span>
          }
        />
        <Row
          label={t('app.sales_inquiry.review_label', { defaultValue: 'Review' })}
          value={
            <span>
              {reviewStatus}
              {spine.review.blocks_convert ? (
                <span className="ml-1 text-xs font-medium text-rose-700">
                  {t('app.sales_inquiry.review_blocks_convert', { defaultValue: 'блокирует Convert' })}
                </span>
              ) : null}
            </span>
          }
        />
        <Row
          label={t('app.sales_inquiry.convert_label', { defaultValue: 'Convert' })}
          value={convertLabel}
        />
        <Row
          label={t('app.sales_inquiry.convert_result_label', { defaultValue: 'Результат Convert' })}
          value={
            clientHref ? (
              <Link to={clientHref} className="font-medium text-brand-700 hover:underline">
                {clientId}
              </Link>
            ) : (
              t('app.sales_inquiry.convert_result_none', { defaultValue: '—' })
            )
          }
        />
        <Row
          label={t('app.sales_inquiry.traceability_label', { defaultValue: 'Traceability' })}
          value={
            spine.traceability.present
              ? t('app.sales_inquiry.traceability_present', { defaultValue: 'lineage записан' })
              : t('app.sales_inquiry.traceability_absent', { defaultValue: 'нет lineage' })
          }
        />
      </dl>
      {spine.sales_inquiry_id ? (
        <p className="mt-2 text-[11px] text-slate-400">
          SI {spine.sales_inquiry_id}
          {spine.inquiry_status ? ` · ${spine.inquiry_status}` : ''}
        </p>
      ) : null}
    </section>
  )
}
