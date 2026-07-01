import { describe, expect, it } from 'vitest'

import { operationalHintForStage, operationalHintForStageResolved } from '../stageOperationalHints'

describe('operationalHintForStage', () => {
  it.each(['rejected', 'declined', 'ready_for_handoff', 'ready_for_hr'])(
    'returns null for pipeline-completed stage %s',
    (code) => {
      expect(operationalHintForStage(code)).toBeNull()
    },
  )

  it('returns assign_vacancy for contacted', () => {
    expect(operationalHintForStage('contacted')).toEqual({ kind: 'assign_vacancy' })
  })
})

describe('operationalHintForStageResolved', () => {
  it('does not resurrect hints for completed stages', () => {
    expect(operationalHintForStageResolved('rejected', 'contacted', { vacancyPipelineBlocking: false })).toBeNull()
  })
})
