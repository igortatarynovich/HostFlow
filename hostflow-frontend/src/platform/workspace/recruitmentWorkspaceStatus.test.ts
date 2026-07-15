import { describe, expect, it } from 'vitest'
import type { RequirementsWorkspaceResponse } from '../../api/candidateRequirements'
import {
  aggregateRecruitmentRequirementsStatus,
  buildCandidateRecruitmentSession,
  getWorkspaceSectionRegistry,
} from './recruitmentWorkspaceStatus'
import { registerRecruitmentWorkspaceSectionsP0 } from '@hostflow/workspace'

const fixture: RequirementsWorkspaceResponse = {
  schema_version: 'requirements_workspace_v1',
  candidate_id: 'cand-1',
  can_edit: true,
  summary: {
    total_requirements: 3,
    fulfilled_count: 1,
    blocking_open_count: 1,
    pending_review_count: 0,
    all_fulfilled: false,
    handoff_ready: false,
  },
  checklist: {
    candidate_id: 'cand-1',
    requirements: [],
    all_fulfilled: false,
  },
  field_requirements: {
    required_fields: [],
    missing_count: 0,
    satisfied: true,
  },
  transfer_readiness: {
    transfer_allowed: false,
    handoff_create_allowed: false,
    blocking_reasons: [],
  },
  pipeline_blockers: {
    unfulfilled_requirements: [
      {
        requirement_code: 'identity_confirmation',
        public_name: 'Identity confirmation',
      },
    ],
  },
  operational_requirements: [],
  evaluated_at: '2026-07-03T00:00:00Z',
}

describe('recruitmentWorkspaceStatus', () => {
  it('aggregates readiness from requirements workspace bundle', async () => {
    const session = buildCandidateRecruitmentSession('cand-1', 'tenant-1')
    const snapshot = await aggregateRecruitmentRequirementsStatus(fixture, session, [
      'candidates.view',
      'candidates.manage',
    ])

    expect(snapshot.aggregated_severity).toBe('blocked')
    expect(snapshot.displayed_next_action?.action_id).toContain('identity_confirmation')
    expect(snapshot.contributions[0]?.blockers?.length).toBeGreaterThan(0)
  })

  it('hides requirements section without candidates.view permission', () => {
    const registry = getWorkspaceSectionRegistry()
    registerRecruitmentWorkspaceSectionsP0(registry)
    const session = buildCandidateRecruitmentSession('cand-1', 'tenant-1')
    const sections = registry.listSections(session, [])
    expect(sections).toHaveLength(0)
  })
})
