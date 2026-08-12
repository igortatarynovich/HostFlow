import { describe, expect, it } from 'vitest'
import {
  computePipelineMetrics,
  stageCountsFromPipelineColumns,
} from '../pipelineMetrics'

describe('stageCountsFromPipelineColumns', () => {
  it('counts by item.stage, not kanban column key', () => {
    const counts = stageCountsFromPipelineColumns({
      new: [{ stage: 'new' }, { stage: 'new' }],
      client_process: [
        { stage: 'employed' },
        { stage: 'employed' },
        { stage: 'processing_by_client' },
      ],
      internal_hr: [{ stage: 'hired' }],
      probation: [{ stage: 'probation_ok' }],
    })
    expect(counts).toEqual({
      new: 2,
      employed: 2,
      processing_by_client: 1,
      hired: 1,
      probation_ok: 1,
    })
  })
})

describe('computePipelineMetrics vacancy progress', () => {
  it('treats employed/hired/probation_ok as hired against headcount', () => {
    const pipe = stageCountsFromPipelineColumns({
      new: [{ stage: 'new' }],
      client_process: [{ stage: 'employed' }, { stage: 'employed' }, { stage: 'employed' }],
      internal_hr: [{ stage: 'hired' }],
      ready: [{ stage: 'ready_for_handoff' }],
    })
    const m = computePipelineMetrics(pipe, 10)
    expect(m.hired).toBe(4)
    expect(m.plan).toBe(10)
    expect(m.remaining).toBe(6)
    expect(m.completionPct).toBe(40)
  })

  it('does not count client_process column key alone as hired', () => {
    // Regression: counting by column key made employed→client_process show 0%.
    const m = computePipelineMetrics({ client_process: 5, new: 2 }, 10)
    expect(m.hired).toBe(0)
    expect(m.completionPct).toBe(0)
  })
})
