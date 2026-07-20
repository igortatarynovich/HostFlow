import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  getLead,
  getLeadQuestionnaireInvite,
  type LeadQuestionnaireInviteResult,
} from '../../api/client'
import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import SalesQuestionnairePanel from '../leads/SalesQuestionnairePanel'
import SalesQuestionnaireAnswersView from '../leads/SalesQuestionnaireAnswersView'
import {
  readSalesQuestionnaireStatus,
  type SalesQuestionnaireStatus,
} from '../../utils/salesQuestionnaire'
import { submissionHasDisplayableAnswers } from '../../utils/salesQuestionnaireSubmission'

/** Hydrate invite only for in-flight invites; never mint on page load. */
const HYDRATE_INVITE_STATUSES: ReadonlySet<SalesQuestionnaireStatus> = new Set([
  'sent',
  'opened',
  'in_progress',
])

const POLL_MS = 12_000

type Props = {
  leadId: string
  onUpdated?: () => void
}

function leadPollFingerprint(row: Lead): string {
  const status = readSalesQuestionnaireStatus(row) || ''
  const submitted = submissionHasDisplayableAnswers(row) ? '1' : '0'
  return `${status}|${submitted}`
}

export default function SalesInquiryQuestionnaireSection({ leadId, onUpdated }: Props) {
  const { t } = useI18n()
  const onUpdatedRef = useRef(onUpdated)
  onUpdatedRef.current = onUpdated
  const tRef = useRef(t)
  tRef.current = t

  const [lead, setLead] = useState<Lead | null>(null)
  const [invite, setInvite] = useState<LeadQuestionnaireInviteResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [inviteLoading, setInviteLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fingerprintRef = useRef<string>('')
  const hydratedStatusRef = useRef<string>('')

  const loadLead = useCallback(async (opts?: { silent?: boolean }) => {
    setError(null)
    if (!opts?.silent) setLoading(true)
    try {
      const row = await getLead(leadId)
      if (row.lead_type !== 'client') {
        setLead(null)
        fingerprintRef.current = ''
        return
      }
      const nextFp = leadPollFingerprint(row)
      const prevFp = fingerprintRef.current
      const changed = nextFp !== prevFp
      fingerprintRef.current = nextFp
      if (changed || !opts?.silent) {
        setLead(row)
      }
      if (opts?.silent && changed && prevFp) {
        onUpdatedRef.current?.()
      }
    } catch (err: unknown) {
      if (!opts?.silent) {
        setLead(null)
        fingerprintRef.current = ''
        const detail =
          (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
          (err as Error)?.message ??
          tRef.current('app.sales_inquiry.questionnaire_load_failed', {
            defaultValue: 'Nie udało się wczytać ankiety',
          })
        setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
      }
    } finally {
      if (!opts?.silent) setLoading(false)
    }
  }, [leadId])

  const hydrateInvite = useCallback(async (row: Lead) => {
    const status = readSalesQuestionnaireStatus(row)
    if (!status || !HYDRATE_INVITE_STATUSES.has(status)) {
      setInvite(null)
      hydratedStatusRef.current = ''
      return
    }
    // Avoid repeat GETs for the same in-flight status (poll / parent refresh).
    if (hydratedStatusRef.current === status) return
    setInviteLoading(true)
    try {
      const result = await getLeadQuestionnaireInvite(row.id)
      setInvite(result)
      hydratedStatusRef.current = status
    } catch (err: unknown) {
      const httpStatus = (err as { response?: { status?: number } })?.response?.status
      if (httpStatus === 404) {
        setInvite(null)
        hydratedStatusRef.current = status
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        tRef.current('app.sales_inquiry.questionnaire_invite_failed', {
          defaultValue: 'Nie udało się pobrać linku ankiety',
        })
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setInviteLoading(false)
    }
  }, [])

  // Initial + leadId change only — never re-bind to unstable parent callbacks.
  useEffect(() => {
    fingerprintRef.current = ''
    hydratedStatusRef.current = ''
    void loadLead()
  }, [loadLead])

  const questionnaireStatus = lead ? readSalesQuestionnaireStatus(lead) : null

  useEffect(() => {
    if (!lead || !questionnaireStatus) return
    void hydrateInvite(lead)
  }, [lead, questionnaireStatus, hydrateInvite])

  /** One poller while waiting — do not reset on every lead object refresh. */
  useEffect(() => {
    if (!questionnaireStatus || !HYDRATE_INVITE_STATUSES.has(questionnaireStatus)) return
    const timer = window.setInterval(() => {
      void loadLead({ silent: true })
    }, POLL_MS)
    return () => window.clearInterval(timer)
  }, [leadId, questionnaireStatus, loadLead])

  const hasAnswers = useMemo(
    () => submissionHasDisplayableAnswers(lead || ({ id: leadId } as Lead)),
    [lead, leadId],
  )
  const status = useMemo(() => readSalesQuestionnaireStatus(lead || {}), [lead])

  const handleLeadUpdated = useCallback(
    (updated: Lead, nextInvite?: LeadQuestionnaireInviteResult | null) => {
      fingerprintRef.current = leadPollFingerprint(updated)
      setLead(updated)
      if (nextInvite) {
        setInvite(nextInvite)
        const st = readSalesQuestionnaireStatus(updated)
        hydratedStatusRef.current = st || ''
      } else {
        const nextStatus = readSalesQuestionnaireStatus(updated)
        hydratedStatusRef.current = ''
        if (nextStatus && HYDRATE_INVITE_STATUSES.has(nextStatus)) {
          void getLeadQuestionnaireInvite(updated.id).then((result) => {
            setInvite(result)
            hydratedStatusRef.current = nextStatus
          })
        } else {
          setInvite(null)
        }
      }
      setError(null)
      onUpdatedRef.current?.()
    },
    [],
  )

  const handleRetry = useCallback(() => {
    void loadLead()
  }, [loadLead])

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Ładowanie…' })}</p>
  }

  if (!lead) return null

  return (
    <div className="space-y-4" data-testid="sales-inquiry-questionnaire">
      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          <p>{error}</p>
          <button type="button" className="mt-2 text-xs font-semibold text-red-900 underline" onClick={handleRetry}>
            {t('common.retry', { defaultValue: 'Spróbuj ponownie' })}
          </button>
        </div>
      ) : null}

      <SalesQuestionnairePanel
        lead={lead}
        invite={invite}
        inviteLoading={inviteLoading}
        hasAnswers={hasAnswers}
        onLeadUpdated={handleLeadUpdated}
        onError={setError}
      />

      {status === 'submitted' || hasAnswers ? <SalesQuestionnaireAnswersView lead={lead} /> : null}
    </div>
  )
}
