import { useCallback, useEffect, useMemo, useState } from 'react'

import { createLeadQuestionnaireInvite, getLead, type LeadQuestionnaireInviteResult } from '../../api/client'
import type { Lead } from '../../api/types'
import { useI18n } from '../../i18n'
import SalesQuestionnairePanel from '../leads/SalesQuestionnairePanel'
import SalesQuestionnaireAnswersView from '../leads/SalesQuestionnaireAnswersView'
import {
  readSalesQuestionnaireStatus,
  type SalesQuestionnaireStatus,
} from '../../utils/salesQuestionnaire'
import { submissionHasDisplayableAnswers } from '../../utils/salesQuestionnaireSubmission'

/** POST hydrate is allowed only for in-flight invites; never on page load for not_sent/submitted. */
const HYDRATE_INVITE_STATUSES: ReadonlySet<SalesQuestionnaireStatus> = new Set([
  'sent',
  'opened',
  'in_progress',
])

type Props = {
  leadId: string
  onUpdated?: () => void
}

export default function SalesInquiryQuestionnaireSection({ leadId, onUpdated }: Props) {
  const { t } = useI18n()
  const [lead, setLead] = useState<Lead | null>(null)
  const [invite, setInvite] = useState<LeadQuestionnaireInviteResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [inviteLoading, setInviteLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadLead = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const row = await getLead(leadId)
      if (row.lead_type !== 'client') {
        setLead(null)
        return
      }
      setLead(row)
    } catch (err: unknown) {
      setLead(null)
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.sales_inquiry.questionnaire_load_failed', { defaultValue: 'Nie udało się wczytać ankiety' })
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setLoading(false)
    }
  }, [leadId, t])

  const hydrateInvite = useCallback(async (row: Lead) => {
    const status = readSalesQuestionnaireStatus(row)
    if (!status || !HYDRATE_INVITE_STATUSES.has(status)) {
      setInvite(null)
      return
    }
    setInviteLoading(true)
    try {
      const result = await createLeadQuestionnaireInvite(row.id, { mark_sent: false })
      setInvite(result)
    } catch (err: unknown) {
      const httpStatus = (err as { response?: { status?: number } })?.response?.status
      if (httpStatus === 404) {
        setInvite(null)
        return
      }
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        t('app.sales_inquiry.questionnaire_invite_failed', { defaultValue: 'Nie udało się pobrać linku ankiety' })
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setInviteLoading(false)
    }
  }, [t])

  useEffect(() => {
    void loadLead()
  }, [loadLead])

  useEffect(() => {
    if (!lead) return
    void hydrateInvite(lead)
  }, [lead, hydrateInvite])

  const hasAnswers = useMemo(() => submissionHasDisplayableAnswers(lead || ({ id: leadId } as Lead)), [lead, leadId])
  const status = useMemo(() => readSalesQuestionnaireStatus(lead || {}), [lead])

  const handleLeadUpdated = useCallback(
    (updated: Lead, nextInvite?: LeadQuestionnaireInviteResult | null) => {
      setLead(updated)
      if (nextInvite) {
        setInvite(nextInvite)
      } else {
        const status = readSalesQuestionnaireStatus(updated)
        if (status && HYDRATE_INVITE_STATUSES.has(status)) {
          void hydrateInvite(updated)
        } else {
          setInvite(null)
        }
      }
      setError(null)
      onUpdated?.()
    },
    [hydrateInvite, onUpdated],
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
