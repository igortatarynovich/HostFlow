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
  return String(ctx.application?.transport_lead_id || '').trim()
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
