import {
  getLead,
  markLeadRodoSourceProvided,
  sendLeadRodoCompliance,
} from '../../../api/client'
import { leadEmailPolicyBlocked, leadRodoNoticeStatus, leadRodoSatisfied } from '../../../utils/intakeResolution'
import type { LeadRodoNoticeStatus } from '../../../utils/intakeResolution'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'

export type ConsentView = {
  available: boolean
  satisfied: boolean
  status: LeadRodoNoticeStatus | null
  policyBlocked: boolean
}

/**
 * Compliance owner facade for capability `consent` (policy `lead_rodo_v1`).
 * Lead transport stays here — capability UI, hosts, and pages must not import
 * getLead / sendLeadRodoCompliance / markLeadRodoSourceProvided.
 */
export function consentSubjectKey(ctx: WorkspaceCapabilityRenderContext): string {
  return resolveLeadId(ctx)
}

function resolveLeadId(ctx: WorkspaceCapabilityRenderContext): string {
  const application = ctx.application
  if (!application) return ''
  const extensions = application.extensions || {}
  const explicit = String(
    application.transport_lead_id || extensions.transport_lead_id || '',
  ).trim()
  if (explicit) return explicit
  // Recruitment ApplicationOut.id is the transport Lead id until R6.
  if (application.module === 'recruitment') return String(application.id || '').trim()
  return ''
}

export async function loadConsent(ctx: WorkspaceCapabilityRenderContext): Promise<ConsentView> {
  const leadId = resolveLeadId(ctx)
  if (!leadId) {
    return { available: false, satisfied: false, status: null, policyBlocked: false }
  }
  const lead = await getLead(leadId)
  return {
    available: true,
    satisfied: leadRodoSatisfied(lead),
    status: leadRodoNoticeStatus(lead),
    policyBlocked: leadEmailPolicyBlocked(lead),
  }
}

export async function sendConsentNotice(ctx: WorkspaceCapabilityRenderContext): Promise<void> {
  const leadId = resolveLeadId(ctx)
  if (!leadId) return
  await sendLeadRodoCompliance(leadId)
}

export async function markConsentCoveredAtSource(ctx: WorkspaceCapabilityRenderContext): Promise<void> {
  const leadId = resolveLeadId(ctx)
  if (!leadId) return
  await markLeadRodoSourceProvided(leadId)
}
