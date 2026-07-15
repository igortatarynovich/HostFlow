import { useCallback, useEffect, useState } from 'react'
import { getEntityProfileFields } from '../../api/intakeForms'
import { getLead } from '../../api/client'
import type { ApplicationContact } from '../../api/types/application'
import type { Lead } from '../../api/types'
import type { FieldOption } from '../../utils/serviceSalesFieldOptions'
import SalesQuestionnaireAnswersPanel from './SalesQuestionnaireAnswersPanel'
import { ClientInformationUpdatesPanel } from './ClientInformationUpdatesPanel'
import { SalesInquiryCommunicationSection } from './SalesInquiryCommunicationSection'

type Props = {
  applicationId: string
  contact: ApplicationContact
  companyName?: string | null
  convertedClientId?: string | null
  onLeadUpdated?: () => void
}

export function SalesInquiryCommunicationBlock({
  applicationId,
  contact,
  companyName,
  convertedClientId,
  onLeadUpdated,
}: Props) {
  const [lead, setLead] = useState<Lead | null>(null)
  const [loading, setLoading] = useState(true)

  const loadLead = useCallback(async () => {
    setLoading(true)
    try {
      setLead(await getLead(applicationId))
    } catch {
      setLead(null)
    } finally {
      setLoading(false)
    }
  }, [applicationId])

  useEffect(() => {
    void loadLead()
  }, [loadLead])

  const handleLeadUpdated = useCallback(
    (next: Lead) => {
      setLead(next)
      onLeadUpdated?.()
    },
    [onLeadUpdated],
  )

  if (loading) return <p className="text-sm text-slate-500">Загрузка…</p>
  if (!lead) return <p className="text-sm text-amber-800">Не удалось загрузить данные отклика.</p>

  return (
    <SalesInquiryCommunicationSection
      lead={lead}
      contact={contact}
      companyName={companyName}
      onLeadUpdated={handleLeadUpdated}
    />
  )
}

export function SalesInquiryAnswersBlock({
  applicationId,
  convertedClientId,
}: {
  applicationId: string
  convertedClientId?: string | null
}) {
  const [lead, setLead] = useState<Lead | null>(null)
  const [optionsByCode, setOptionsByCode] = useState<Record<string, FieldOption[]>>({})
  const [dismissedUpdates, setDismissedUpdates] = useState(false)

  useEffect(() => {
    let cancelled = false
    void getLead(applicationId)
      .then((row) => {
        if (!cancelled) setLead(row)
      })
      .catch(() => {
        if (!cancelled) setLead(null)
      })
    return () => {
      cancelled = true
    }
  }, [applicationId])

  useEffect(() => {
    let cancelled = false
    void getEntityProfileFields('service_sales.targeted_advertising')
      .then((profile) => {
        if (cancelled) return
        const map: Record<string, FieldOption[]> = {}
        for (const field of profile.fields) {
          if (field.options?.length) map[field.qualified_code] = field.options
        }
        setOptionsByCode(map)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [])

  if (!lead) return null

  return (
    <div className="space-y-4">
      {!dismissedUpdates ? (
        <ClientInformationUpdatesPanel
          lead={lead}
          convertedClientId={convertedClientId}
          optionsByCode={optionsByCode}
          onApply={() => {
            // Backend apply-to-client endpoint — next platform slice
            setDismissedUpdates(true)
          }}
          onDismiss={() => setDismissedUpdates(true)}
        />
      ) : null}
      <SalesQuestionnaireAnswersPanel lead={lead} />
    </div>
  )
}

/** @deprecated use SalesInquiryCommunicationBlock + SalesInquiryAnswersBlock */
export function SalesInquiryQuestionnaireSection({
  applicationId,
  contact,
  companyName,
  onLeadUpdated,
}: Props) {
  return (
    <SalesInquiryCommunicationBlock
      applicationId={applicationId}
      contact={contact}
      companyName={companyName}
      onLeadUpdated={onLeadUpdated}
    />
  )
}

export function SalesInquiryAttributionSection({ applicationId }: { applicationId: string }) {
  return (
    <dl className="grid gap-2 text-sm">
      <div>
        <dt className="text-xs text-slate-500">Режим</dt>
        <dd className="font-medium text-slate-900">Ответы дополняют этот отклик</dd>
      </div>
    </dl>
  )
}
