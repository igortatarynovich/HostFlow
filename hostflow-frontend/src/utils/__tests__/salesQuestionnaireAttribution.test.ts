import { describe, expect, it } from 'vitest'

import {
  readSubmissionPolicyMode,
  readSubmissionPublishedVersion,
  readSubmissionSource,
  submissionEntryLabel,
  submissionPolicyModeLabel,
} from '../salesQuestionnaireAttribution'

describe('salesQuestionnaireAttribution', () => {
  it('reads source and policy from submission snapshot', () => {
    const submission = {
      source: { entry: 'questionnaire_invite', invite_id: 'invite-123' },
      effective_submission_policy: { submission_policy: { mode: 'attach' } },
      published_version: 1,
    }
    expect(readSubmissionSource(submission)).toEqual({ entry: 'questionnaire_invite', invite_id: 'invite-123' })
    expect(readSubmissionPolicyMode(submission)).toBe('attach')
    expect(readSubmissionPublishedVersion(submission)).toBe(1)
  })

  it('maps entry and policy codes to operator labels', () => {
    expect(submissionEntryLabel('questionnaire_invite')).toBe('Personal questionnaire invite')
    expect(submissionPolicyModeLabel('attach')).toBe('Added to this inquiry')
  })
})
