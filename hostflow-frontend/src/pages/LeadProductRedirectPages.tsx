import { useEffect, useState } from 'react'
import { Navigate, useLocation, useParams } from 'react-router-dom'

import { getSalesInquiry } from '../api/applications'
import { getLead } from '../api/client'
import {
  isClientTransportLead,
  leadDetailRedirectPath,
  leadIndexRedirectPath,
} from '../app/leadProductRedirect'

/** `/app/leads` is not a mixed Recruitment+Sales inbox. */
export function LeadsIndexRedirect() {
  const location = useLocation()
  return <Navigate to={leadIndexRedirectPath(location.search)} replace />
}

/** `/app/leads/:id` is a compat hop, never the work card. */
export function LeadWorkspaceRedirect() {
  const { leadId } = useParams<{ leadId: string }>()
  const [to, setTo] = useState<string | null>(null)
  const [missing, setMissing] = useState(false)

  useEffect(() => {
    const id = String(leadId || '').trim()
    if (!id) {
      setMissing(true)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const lead = await getLead(id)
        if (cancelled) return
        let salesInquiryId: string | null = null
        if (isClientTransportLead(lead)) {
          try {
            const inquiry = await getSalesInquiry(id)
            salesInquiryId = inquiry.id || inquiry.sales_inquiry_id || null
          } catch {
            salesInquiryId = id
          }
        }
        if (cancelled) return
        setTo(
          leadDetailRedirectPath({
            leadId: id,
            leadType: lead.lead_type,
            leadTargetType: lead.lead_target_type,
            salesInquiryId,
          }),
        )
      } catch {
        if (!cancelled) setMissing(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [leadId])

  if (missing) {
    return <Navigate to={leadIndexRedirectPath('')} replace />
  }
  if (!to) {
    return null
  }
  return <Navigate to={to} replace />
}

export default LeadWorkspaceRedirect
