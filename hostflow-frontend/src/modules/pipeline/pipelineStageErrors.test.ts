/** @vitest-environment node */
import { describe, expect, it } from 'vitest';

import { formatMissingPipelineDocTypes, parseStageTransitionError } from './pipelineStageErrors';

describe('parseStageTransitionError', () => {
  it('detects handoff_docs_incomplete from object detail', () => {
    const e = {
      response: {
        data: {
          detail: { code: 'handoff_docs_incomplete', missing_types: ['passport', 'id'] },
        },
      },
    };
    expect(parseStageTransitionError(e)).toEqual({
      kind: 'handoff_docs',
      missingTypes: ['passport', 'id'],
    });
  });

  it('detects rodo gate from string detail', () => {
    const e = { response: { data: { detail: 'Rodo must be sent before stage change' } } };
    expect(parseStageTransitionError(e)).toEqual({ kind: 'rodo', missingTypes: [] });
  });

  it('returns other for unknown errors', () => {
    expect(parseStageTransitionError(new Error('x'))).toEqual({ kind: 'other', missingTypes: [] });
  });
});

describe('formatMissingPipelineDocTypes', () => {
  it('returns em dash when empty', () => {
    expect(formatMissingPipelineDocTypes([], (c) => c)).toBe('—');
  });

  it('dedupes and joins with label fn', () => {
    expect(
      formatMissingPipelineDocTypes(['a', 'a', 'b'], (c) => c.toUpperCase()),
    ).toBe('A, B');
  });
});
