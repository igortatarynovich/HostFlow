/** @vitest-environment node */
import { describe, expect, it } from 'vitest';

import type { PipelineOut } from '../../api/types';
import {
  buildFilteredPipelineColumns,
  computePipelineColumnInsights,
  pipelineColumnItemMatches,
} from './filterPipelineColumns';

const emptyFilters = {
  search: '',
  manager: '',
  citizenship: '',
  docs: '',
  from: '',
  to: '',
};

describe('pipelineColumnItemMatches', () => {
  it('matches search by name', () => {
    const item = { candidate: { first_name: 'Anna', last_name: 'Smith' } };
    expect(pipelineColumnItemMatches(item, { ...emptyFilters, search: 'anna' })).toBe(true);
    expect(pipelineColumnItemMatches(item, { ...emptyFilters, search: 'zzz' })).toBe(false);
  });

  it('matches manager filter on recruiter_id', () => {
    const item = { candidate: { recruiter_id: 'u1' } };
    expect(pipelineColumnItemMatches(item, { ...emptyFilters, manager: 'u1' })).toBe(true);
    expect(pipelineColumnItemMatches(item, { ...emptyFilters, manager: 'u2' })).toBe(false);
  });
});

describe('buildFilteredPipelineColumns', () => {
  it('returns sorted filtered columns', () => {
    const data = {
      statuses: ['a'],
      columns: {
        col1: [
          {
            candidate: { id: '1', created_at: '2020-01-01T00:00:00Z' },
            stage: 'new',
          },
          {
            candidate: { id: '2', created_at: '2021-01-01T00:00:00Z' },
            stage: 'new',
          },
        ],
      },
    } as unknown as PipelineOut;
    const out = buildFilteredPipelineColumns(data, ['col1'], emptyFilters);
    expect(out.col1?.map((x: any) => x.candidate.id)).toEqual(['2', '1']);
  });
});

describe('computePipelineColumnInsights', () => {
  it('counts total and new stages', () => {
    const filtered = {
      c: [
        { stage: 'new', candidate: {} },
        { stage: 'contacted', candidate: {} },
      ],
    };
    expect(computePipelineColumnInsights(filtered, ['c'])).toEqual({
      total: 2,
      newCount: 1,
      docsReady: 0,
      docsAttention: 0,
    });
  });
});
