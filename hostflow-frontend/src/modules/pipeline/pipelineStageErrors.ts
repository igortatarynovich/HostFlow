/**
 * Pipeline bulk / drag stage transition error parsing (API detail shapes).
 */

export type PipelineStageErrorKind = 'rodo' | 'handoff_docs' | 'other';

export type PipelineStageTransitionParse = {
  kind: PipelineStageErrorKind;
  missingTypes: string[];
};

export function parseStageTransitionError(rawError: unknown): PipelineStageTransitionParse {
  const err = rawError as { response?: { data?: { detail?: unknown } } };
  const detailRaw = err?.response?.data?.detail;
  const toMissing = (val: unknown): string[] =>
    Array.isArray(val) ? val.map((x) => String(x || '').trim()).filter(Boolean) : [];

  const parseDetailObject = (value: unknown): Record<string, unknown> | null => {
    if (value && typeof value === 'object') return value as Record<string, unknown>;
    if (typeof value !== 'string') return null;
    const text = value.trim();
    if (!text.startsWith('{')) return null;
    try {
      const parsed = JSON.parse(text) as unknown;
      return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null;
    } catch {
      return null;
    }
  };

  const detailObj = parseDetailObject(detailRaw);
  const detailText = String(detailRaw || '').toLowerCase();
  if (detailObj && String(detailObj.code || '') === 'handoff_docs_incomplete') {
    return { kind: 'handoff_docs', missingTypes: toMissing(detailObj.missing_types) };
  }
  if (detailText.includes('handoff_docs_incomplete')) {
    return { kind: 'handoff_docs', missingTypes: toMissing(detailObj?.missing_types) };
  }
  if (detailText.includes('rodo must be sent') || detailText.includes('contact/screening stage')) {
    return { kind: 'rodo', missingTypes: [] };
  }
  return { kind: 'other', missingTypes: [] };
}

/** Human list of doc type codes; `labelForCode` typically wraps i18n `admin.documents.types.*`. */
export function formatMissingPipelineDocTypes(
  codes: string[],
  labelForCode: (code: string) => string,
): string {
  const unique = Array.from(new Set(codes.map((c) => String(c || '').trim()).filter(Boolean)));
  if (!unique.length) return '—';
  return unique.map((code) => labelForCode(code)).join(', ');
}
