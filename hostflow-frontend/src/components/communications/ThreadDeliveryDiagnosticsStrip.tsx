import { useEffect, useState } from 'react'
import {
  getMessageDeliveryDiagnostics,
  type CommunicationMessage,
  type DeliveryDiagnostics,
} from '../../api/communications'
import { useI18n } from '../../i18n'

/** C1.3: prefer ThreadContext.workspace.delivery_summary; deep-dive via message diagnostics. */
export default function ThreadDeliveryDiagnosticsStrip({
  messages,
  deliverySummary,
}: {
  messages: CommunicationMessage[]
  deliverySummary?: {
    message_id?: string
    status?: string
    reason_code?: string | null
    retryable?: boolean | null
    next_retry_at?: string | null
    safe_message?: string | null
    latest_status?: string
    error_message?: string
    message?: string
  } | null
}) {
  const { t } = useI18n()
  const [diag, setDiag] = useState<DeliveryDiagnostics | null>(null)

  const summaryStatus = String(deliverySummary?.status || deliverySummary?.latest_status || '').toLowerCase()
  const summaryFailed = ['failed', 'undeliverable', 'bounced', 'rejected', 'error'].includes(summaryStatus)
  const summaryReason =
    (deliverySummary?.reason_code as string | undefined) ||
    (deliverySummary?.error_message as string | undefined) ||
    (deliverySummary?.message as string | undefined)

  const failedOutbound = [...messages]
    .reverse()
    .find(
      (m) =>
        m.direction === 'outbound' &&
        ['failed', 'undeliverable', 'bounced', 'rejected'].includes(
          String(m.delivery_status || '').toLowerCase(),
        ),
    )

  useEffect(() => {
    let cancelled = false
    if (!failedOutbound?.id || (summaryFailed && summaryReason)) {
      setDiag(null)
      return
    }
    void getMessageDeliveryDiagnostics(String(failedOutbound.id))
      .then((d) => {
        if (!cancelled) setDiag(d)
      })
      .catch(() => {
        if (!cancelled) setDiag(null)
      })
    return () => {
      cancelled = true
    }
  }, [failedOutbound?.id, summaryFailed, summaryReason])

  if (summaryFailed || (deliverySummary && summaryStatus && summaryStatus !== 'ok' && summaryStatus !== 'delivered')) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
        <div className="font-semibold">
          {t('app.communications.delivery_diagnostics.title', {
            defaultValue: 'Delivery issue',
          })}
        </div>
        <div className="mt-0.5">
          {t('app.communications.delivery_diagnostics.status', { defaultValue: 'Status' })}:{' '}
          <span className="font-medium">{summaryStatus || 'issue'}</span>
          {summaryReason ? (
            <>
              {' · '}
              {t('app.communications.delivery_diagnostics.reason', { defaultValue: 'Reason' })}:{' '}
              <span className="font-medium">{String(summaryReason)}</span>
            </>
          ) : null}
        </div>
      </div>
    )
  }

  if (!failedOutbound || !diag) return null

  const reason =
    (diag.last_attempt?.reason_code as string | undefined) ||
    failedOutbound.error_message ||
    diag.status
  const retryable = diag.last_attempt?.retryable

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
      <div className="font-semibold">
        {t('app.communications.delivery_diagnostics.title', {
          defaultValue: 'Delivery issue',
        })}
      </div>
      <div className="mt-0.5">
        {t('app.communications.delivery_diagnostics.status', { defaultValue: 'Status' })}:{' '}
        <span className="font-medium">{diag.status}</span>
        {reason ? (
          <>
            {' · '}
            {t('app.communications.delivery_diagnostics.reason', { defaultValue: 'Reason' })}:{' '}
            <span className="font-medium">{String(reason)}</span>
          </>
        ) : null}
        {retryable === true ? (
          <>
            {' · '}
            {t('app.communications.delivery_diagnostics.retryable', { defaultValue: 'Retryable' })}
          </>
        ) : retryable === false ? (
          <>
            {' · '}
            {t('app.communications.delivery_diagnostics.not_retryable', {
              defaultValue: 'Not retryable',
            })}
          </>
        ) : null}
      </div>
      {diag.next_retry_at ? (
        <div className="mt-0.5 text-amber-900/80">
          {t('app.communications.delivery_diagnostics.next_retry', {
            defaultValue: 'Next retry',
          })}
          : {diag.next_retry_at}
        </div>
      ) : null}
    </div>
  )
}
