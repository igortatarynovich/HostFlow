// @vitest-environment node
import { describe, expect, it } from 'vitest'
import {
  assertNoEmployeeCreated,
  buildResolutionPatchForNextStep,
  decisionSurfaceMode,
  operatorCanResolveCurrentGap,
  shouldShowPathwaySelector,
  wouldReaskKnownPackageFact,
} from '../employmentDecisionUi'

describe('employmentDecisionUi (ESO-2+3 Decision Surface)', () => {
  it('branch: accepted → employable → ready for Formalize', () => {
    const surface = decisionSurfaceMode({
      decision: 'employable',
      next_step: { code: 'proceed_to_formalize', label: 'Proceed to Formalize' },
      employee_created: false,
    })
    expect(surface.mode).toBe('employable')
    expect(surface.readyForFormalize).toBe(true)
    expect(operatorCanResolveCurrentGap({ decision: 'employable' })).toBe(false)
    expect(assertNoEmployeeCreated({ decision: 'employable', employee_created: false })).toBe(true)
  })

  it('branch: insufficient_facts → one missing → resolve patch → auto re-eval path', () => {
    const missing = {
      decision: 'insufficient_facts' as const,
      next_step: {
        code: 'provide_citizenship',
        label: 'Provide citizenship (ISO alpha-2)',
      },
      employee_created: false,
    }
    expect(decisionSurfaceMode(missing).mode).toBe('insufficient_facts')
    expect(operatorCanResolveCurrentGap(missing)).toBe(true)
    const patch = buildResolutionPatchForNextStep('provide_citizenship', { citizenship: 'pl' })
    expect(patch).toEqual({ facts: { citizenship: 'PL' } })
    // After resolve, ESO-3 returns employability — surface flips to employable.
    expect(
      decisionSurfaceMode({
        decision: 'employable',
        next_step: { code: 'proceed_to_formalize' },
      }).readyForFormalize,
    ).toBe(true)
  })

  it('branch: blocked → reason / no fake action', () => {
    const blocked = {
      decision: 'blocked' as const,
      next_step: { code: 'fix_package', label: 'Fix ready_for_employment.v1 package' },
      blockers: [{ code: 'invalid_package', message: 'Package invalid' }],
    }
    expect(decisionSurfaceMode(blocked).mode).toBe('blocked')
    expect(operatorCanResolveCurrentGap(blocked)).toBe(false)
  })

  it('zero-choice: never show pathway selector; do not re-ask known citizenship', () => {
    expect(
      shouldShowPathwaySelector({
        decision: 'employable',
        legal_pathway: { pathway_id: 'pl_eu_eea_free_movement', selection_required: false },
        pathway_selection_required: false,
      }),
    ).toBe(false)
    expect(
      wouldReaskKnownPackageFact('citizenship', { citizenship: 'PL' }),
    ).toBe(true)
    expect(
      wouldReaskKnownPackageFact('citizenship', { citizenship: null }),
    ).toBe(false)
  })

  it('work authorization evidence builds evidence patch only', () => {
    expect(
      buildResolutionPatchForNextStep('provide_work_authorization_evidence', {
        workAuthorizationPresent: true,
      }),
    ).toEqual({ evidence: { has_work_authorization: true } })
    expect(
      buildResolutionPatchForNextStep('provide_work_authorization_evidence', {
        workAuthorizationPresent: false,
      }),
    ).toBeNull()
  })
})
