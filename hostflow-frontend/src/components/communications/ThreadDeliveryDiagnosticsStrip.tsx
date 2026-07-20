import { useEffect, useState } from 'react'
import {
  getMessageDeliveryDiagnostics,
  type CommunicationMessage,
  type DeliveryDiagnostics,
} from '../../api/communications'
import { useI18n } from '../../i18n'

/** C1: operator-facing delivery facts on the Thread card (C0.3 contract). */
export default function ThreadDeliveryDiagnosticsStrip({
  messages,
}: {
  messages: CommunicationMessage[]
}) {
  const { t } = useI18n()
  const [diag, setDiag] = useState<DeliveryDiagnostics | null>(null)

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
    if (!failedOutbound?.id) {
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
  }, [failedOutbound?.id])

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
