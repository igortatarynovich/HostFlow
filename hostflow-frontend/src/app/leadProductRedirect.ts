import { CRM_APP_PATHS } from './crmAppPaths'
import { recruitmentApplicationPath, RECRUITMENT_INBOX_PATH } from './recruitmentInboxPaths'
import { salesInquiryPath, SALES_HOME_PATH } from './salesPaths'

/** Client/Sales transport Lead — not a Recruitment Application. */
export function isClientTransportLead(lead: {
  lead_type?: string | null
  lead_target_type?: string | null
}): boolean {
  const type = String(lead.lead_type || '').trim().toLowerCase()
  const target = String(lead.lead_target_type || '').trim().toLowerCase()
  return type === 'client' || target === 'client_lead'
}

/**
 * Mixed `/app/leads` inbox is gone.
 * Diagnostic statuses stay on Meta admin; everything else leaves the Lead kanban.
 */
export function leadIndexRedirectPath(search: string): string {
  const raw = search.startsWith('?') ? search.slice(1) : search
  const status = (new URLSearchParams(raw).get('status') || '').trim().toLowerCase()
  if (status === 'needs_routing' || status === 'failed') {
    return CRM_APP_PATHS.settingsIntegrationsMeta
  }
  return `${SALES_HOME_PATH}/inquiries`
}

/** Compat `/app/leads/:id` → owning module workspace. */
export function leadDetailRedirectPath(args: {
  leadId: string
  leadType?: string | null
  leadTargetType?: string | null
  salesInquiryId?: string | null
}): string {
  if (isClientTransportLead({ lead_type: args.leadType, lead_target_type: args.leadTargetType })) {
    return salesInquiryPath(String(args.salesInquiryId || args.leadId))
  }
  return recruitmentApplicationPath(args.leadId)
}

export { RECRUITMENT_INBOX_PATH }
