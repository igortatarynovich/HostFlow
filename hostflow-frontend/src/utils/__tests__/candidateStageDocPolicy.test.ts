import { describe, expect, it } from 'vitest'

import {
  DEFAULT_HIRING_PIPELINE_GATES_RUNTIME,
  docsPipelineBlocksForwardResolved,
} from '../candidateStageDocPolicy'

describe('docsPipelineBlocksForwardResolved', () => {
  const gates = DEFAULT_HIRING_PIPELINE_GATES_RUNTIME
  const blockers = { missing: ['passport_scan'] as string[], problematic: [] as string[], inProgress: [] as string[] }

  it.each(['rejected', 'declined', 'ready_for_handoff', 'ready_for_hr'] as const)(
    'does not hard/soft block when stage is pipeline-completed (%s)',
    (stage) => {
      const r = docsPipelineBlocksForwardResolved(stage, blockers, false, gates)
      expect(r).toEqual({ hard: false, softWarnOnly: false })
    },
  )

  it('still hard-blocks active stage with missing documents', () => {
    const r = docsPipelineBlocksForwardResolved('docs_wait', blockers, false, gates)
    expect(r.hard).toBe(true)
    expect(r.softWarnOnly).toBe(false)
  })

  it('returns no block while summary is loading', () => {
    const r = docsPipelineBlocksForwardResolved('docs_wait', blockers, true, gates)
    expect(r).toEqual({ hard: false, softWarnOnly: false })
  })
})
