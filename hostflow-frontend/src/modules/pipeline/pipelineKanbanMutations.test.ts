/** @vitest-environment node */
import { describe, expect, it } from 'vitest';
import {
  buildBulkColumnStagePlansFromMatrix,
  summarizeBulkStageRejectionStats,
} from './pipelineKanbanMutations';

describe('summarizeBulkStageRejectionStats', () => {
  it('counts rodo vs handoff_docs rejections', () => {
    const rejected = [
      { status: 'rejected' as const, reason: { response: { data: { detail: 'rodo must be sent' } } } },
      {
        status: 'rejected' as const,
        reason: { response: { data: { detail: { code: 'handoff_docs_incomplete', missing_types: ['a'] } } } },
      },
    ];
    const s = summarizeBulkStageRejectionStats(rejected);
    expect(s.rodoBlocked).toBe(1);
    expect(s.docsBlocked).toBe(1);
    expect(s.missingByDocs).toContain('a');
  });
});

describe('buildBulkColumnStagePlansFromMatrix', () => {
  it('builds per-id plans using buildStagePath', () => {
    const columns = {
      new: [{ candidate_id: '1', stage: 'new', candidate: { id: '1', stage: 'new' } }],
    };
    const plans = buildBulkColumnStagePlansFromMatrix(columns, ['1'], 'interview', (from, col) => ({
      targetStage: col === 'interview' ? 'contacted' : 'x',
      stages: from ? ['contacted'] : [],
    }));
    expect(plans['1']?.targetStage).toBe('contacted');
  });
});
