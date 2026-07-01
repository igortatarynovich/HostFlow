/** @vitest-environment node */
import { describe, expect, it } from 'vitest';
import { parseVacancyPipelineProfileStagesPatch } from './parseVacancyPipelineProfilePatch';

describe('parseVacancyPipelineProfileStagesPatch', () => {
  it('returns null profile when missing', () => {
    expect(parseVacancyPipelineProfileStagesPatch({}).profile).toBeNull();
  });

  it('extracts column order from profile', () => {
    const patch = parseVacancyPipelineProfileStagesPatch({
      profile_stages: {
        column_order: ['new', 'interview'],
        stage_columns: { new: ['new'] },
        stage_codes: ['new'],
      },
    });
    expect(patch.profile).not.toBeNull();
    expect(patch.columnOrder).toEqual(['new', 'interview']);
    expect(patch.columnStages?.new).toEqual(['new']);
    expect(patch.stageSequence).toEqual(['new']);
  });
});
