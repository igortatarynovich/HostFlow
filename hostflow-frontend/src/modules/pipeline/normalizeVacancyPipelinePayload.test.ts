/** @vitest-environment node */
import { describe, expect, it } from 'vitest';
import {
  normalizeVacancyPipelinePayload,
  rebuildPipelineColumnsFromCandidates,
} from './normalizeVacancyPipelinePayload';

describe('normalizeVacancyPipelinePayload', () => {
  it('flattens array-shaped columns from API', () => {
    const raw = {
      columns: [{ code: 'new', items: [{ candidate_id: 'c1', candidate: { id: 'c1' } }] }],
    };
    const { normalized, total } = normalizeVacancyPipelinePayload(raw as any, []);
    expect(normalized.columns?.new?.length).toBe(1);
    expect(normalized.columns?.new?.[0]?.candidate_id).toBe('c1');
    expect(total).toBe(1);
  });
});

describe('rebuildPipelineColumnsFromCandidates', () => {
  it('groups flat candidates by stageToColumn', () => {
    const raw = {};
    const rows = [
      {
        id: 'a',
        stage: 'contacted',
        vacancy_id: 'v1',
      },
    ];
    const stageToColumn: Record<string, string> = { contacted: 'interview' };
    const out = rebuildPipelineColumnsFromCandidates(raw as any, rows, ['new'], stageToColumn);
    expect(out.columns?.interview?.length).toBe(1);
    expect(out.statuses).toContain('interview');
  });
});
