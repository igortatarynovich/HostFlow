import { describe, expect, it } from 'vitest'

import { APP_ROUTES } from '../routes'
import {
  isClientTransportLead,
  leadDetailRedirectPath,
  leadIndexRedirectPath,
} from '../leadProductRedirect'

describe('leadProductRedirect', () => {
  it('treats client / client_lead as Sales transport', () => {
    expect(isClientTransportLead({ lead_type: 'client', lead_target_type: 'client_lead' })).toBe(true)
    expect(isClientTransportLead({ lead_type: 'candidate', lead_target_type: 'candidate' })).toBe(false)
  })

  it('sends diagnostic Lead list queries to Meta admin', () => {
    expect(leadIndexRedirectPath('?status=needs_routing')).toBe('/app/settings/integrations/meta')
    expect(leadIndexRedirectPath('status=failed')).toBe('/app/settings/integrations/meta')
  })

  it('does not keep a mixed Lead inbox for the default list', () => {
    expect(leadIndexRedirectPath('')).toBe('/app/sales/inquiries')
    expect(leadIndexRedirectPath('?filter=no_first_contact_24h')).toBe('/app/sales/inquiries')
  })

  it('opens client transport on SalesInquiry workspace', () => {
    expect(
      leadDetailRedirectPath({
        leadId: 'lead-1',
        leadType: 'client',
        leadTargetType: 'client_lead',
        salesInquiryId: 'si-9',
      }),
    ).toBe('/app/sales/inquiries/si-9')
  })

  it('opens recruitment transport on Application workspace', () => {
    expect(
      leadDetailRedirectPath({
        leadId: 'lead-2',
        leadType: 'candidate',
        leadTargetType: 'candidate',
      }),
    ).toBe('/app/recruitment/inbox/lead-2')
  })

  it('wires /app/leads routes to the product redirectors, not LeadDetailPage', () => {
    const detail = APP_ROUTES.find((r) => r.key === 'lead-detail')
    const index = APP_ROUTES.find((r) => r.key === 'leads')
    expect(detail?.Component.name).toMatch(/LeadWorkspaceRedirect/)
    expect(index?.Component.name).toMatch(/LeadsIndexRedirect/)
  })
})
