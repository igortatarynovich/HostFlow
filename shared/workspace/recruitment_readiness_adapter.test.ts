/**
 * @see recruitment_readiness_adapter.ts
 */
import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  buildRecruitmentReadinessBlockers,
  pickRecruitmentNextAction,
  recruitmentReadinessFromWorkspace,
  type RecruitmentWorkspaceReadinessInput,
} from './recruitment_readiness_adapter.ts'

const baseInput: RecruitmentWorkspaceReadinessInput = {
  candidate_id: 'cand-1',
  summary: {
    total_requirements: 5,
    fulfilled_count: 2,
    blocking_open_count: 2,
    pending_review_count: 0,
    all_fulfilled: false,
    handoff_ready: false,
  },
  field_requirements: {
    required_fields: [],
    missing_count: 0,
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
  checklist: {
    requirements: [
      {
        requirement_code: 'identity_confirmation',
        public_name: 'Identity confirmation',
        fulfilled: false,
      },
    ],
  },
}

describe('recruitment readiness adapter', () => {
  it('maps blocking workspace to blocked severity and blockers', () => {
    const contribution = recruitmentReadinessFromWorkspace(baseInput, {
      candidateRequirementsPath: '/app/candidates/cand-1/requirements',
    })

    assert.equal(contribution.severity, 'blocked')
    assert.ok(contribution.blockers?.some((b) => b.block_id === 'requirement:identity_confirmation'))
  })

  it('picks first unfulfilled requirement as next action', () => {
    const action = pickRecruitmentNextAction(baseInput, '/app/candidates/cand-1/requirements')
    assert.equal(action?.action_id, 'close_requirement:identity_confirmation')
    assert.match(String(action?.handler_ref), /identity_confirmation/)
  })

  it('returns handoff next action when ready', () => {
    const action = pickRecruitmentNextAction(
      {
        ...baseInput,
        summary: {
          ...baseInput.summary,
          blocking_open_count: 0,
          all_fulfilled: true,
          handoff_ready: true,
        },
        transfer_readiness: {
          transfer_allowed: true,
          handoff_create_allowed: true,
          blocking_reasons: [],
        },
        pipeline_blockers: {},
      },
      '/app/candidates/cand-1/requirements',
    )
    assert.equal(action?.action_id, 'start_handoff')
  })

  it('includes pending review as warning blockers', () => {
    const blockers = buildRecruitmentReadinessBlockers({
      ...baseInput,
      pipeline_blockers: {
        pending_review_requirements: ['driving_qualification'],
        unfulfilled_requirements: [],
      },
      checklist: {
        requirements: [
          {
            requirement_code: 'driving_qualification',
            public_name: 'Driving qualification',
            fulfilled: false,
            evaluation: { status: 'pending_verification' },
          },
        ],
      },
    })
    assert.ok(blockers.some((b) => b.severity === 'warning'))
  })
})
