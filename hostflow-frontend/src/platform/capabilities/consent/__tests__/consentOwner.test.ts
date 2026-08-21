import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'
import {
  consentSubjectKey,
  loadConsent,
  markConsentCoveredAtSource,
  sendConsentNotice,
} from '../consentOwner'

const getLead = vi.fn()
const sendLeadRodoCompliance = vi.fn()
const markLeadRodoSourceProvided = vi.fn()

vi.mock('../../../../api/client', () => ({
  getLead: (...args: unknown[]) => getLead(...args),
  sendLeadRodoCompliance: (...args: unknown[]) => sendLeadRodoCompliance(...args),
  markLeadRodoSourceProvided: (...args: unknown[]) => markLeadRodoSourceProvided(...args),
}))

function ctx(
  patch: Partial<WorkspaceCapabilityRenderContext> = {},
): WorkspaceCapabilityRenderContext {
  return {
    patching: false,
    onClose: () => undefined,
    onRefresh: () => undefined,
    ...patch,
  }
}

describe('consentOwner', () => {
  beforeEach(() => {
    getLead.mockReset()
    sendLeadRodoCompliance.mockReset()
    markLeadRodoSourceProvided.mockReset()
  })

  it('hides Lead transport when there is no intake id', async () => {
    const subject = ctx({
      application: {
        id: 'app-1',
        module: 'recruitment',
        contact: { name: 'Ada' },
        title: 'Ada',
        status: 'new',
        tab_bucket: 'new',
      },
    })
    expect(consentSubjectKey(subject)).toBe('')
    await expect(loadConsent(subject)).resolves.toEqual({
      available: false,
      satisfied: false,
      status: null,
      policyBlocked: false,
    })
    expect(getLead).not.toHaveBeenCalled()
  })

  it('loads and mutates consent only through Lead transport inside the owner', async () => {
    getLead.mockResolvedValue({ candidate_id: 'cand-1', normalized: {} })
    const subject = ctx({
      application: {
        id: 'app-1',
        module: 'recruitment',
        contact: { name: 'Ada' },
        title: 'Ada',
        status: 'new',
        tab_bucket: 'new',
        transport_lead_id: 'lead-7',
      },
    })
    expect(consentSubjectKey(subject)).toBe('lead-7')
    const view = await loadConsent(subject)
    expect(getLead).toHaveBeenCalledWith('lead-7')
    expect(view.available).toBe(true)
    expect(view.satisfied).toBe(true)
    await sendConsentNotice(subject)
    expect(sendLeadRodoCompliance).toHaveBeenCalledWith('lead-7')
    await markConsentCoveredAtSource(subject)
    expect(markLeadRodoSourceProvided).toHaveBeenCalledWith('lead-7')
  })
})
