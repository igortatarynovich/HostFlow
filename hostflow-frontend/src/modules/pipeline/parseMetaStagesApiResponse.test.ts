/** @vitest-environment node */
import { describe, expect, it } from 'vitest';
import { parseMetaStagesApiResponse } from './parseMetaStagesApiResponse';

describe('parseMetaStagesApiResponse', () => {
  it('maps array body to stage sequence', () => {
    const patch = parseMetaStagesApiResponse([' new ', 'interview']);
    expect(patch.stageSequence).toEqual(['new', 'interview']);
    expect(patch.columnStages).toBeUndefined();
  });

  it('keeps employment stages from funnel order', () => {
    const patch = parseMetaStagesApiResponse({
      order: ['new', 'employed', 'rejected'],
    });
    expect(patch.stageSequence).toEqual(['new', 'employed', 'rejected']);
  });

  it('merges groups with defaults and derives column order', () => {
    const patch = parseMetaStagesApiResponse({
      groups: { new: ['new'], interview: ['contacted'] },
    });
    expect(patch.columnStages?.new).toContain('new');
    expect(patch.columnOrder?.includes('new')).toBe(true);
    expect(patch.stageSequence?.length).toBeGreaterThan(0);
  });

  it('returns empty patch for non-object non-array', () => {
    expect(parseMetaStagesApiResponse(null)).toEqual({});
    expect(parseMetaStagesApiResponse(undefined)).toEqual({});
  });
});
