/**
 * Utility functions for candidates module
 */

import { DOC_READINESS_META, DOC_READINESS_ORDER } from './constants';
import type { UICandidate, DocsMeta, CandidateExtraNormalized } from './types';
import {
  sanitizeDocsProgress,
  firstNonEmpty,
  normalizeDateString,
  toTimestamp,
  extractExtraObject,
} from './candidateUtils';

export function deriveDocsMeta(candidate: UICandidate): DocsMeta {
  const progress = sanitizeDocsProgress(candidate.docs_progress);

  const readinessRaw = firstNonEmpty(
    candidate.docs_readiness_state,
    progress.readiness_state,
    progress.readinessState,
    progress.state,
  ).toLowerCase();

  let readiness = readinessRaw;

  const orderedAt = normalizeDateString(
    candidate.docs_last_ordered_at ??
      progress.last_ordered_at ??
      progress.ordered_at ??
      progress.orderedAt ??
      progress.timeline?.ordered_at ??
      progress.timeline?.orderedAt ??
      progress.most_recent_ordered_at ??
      null,
  );

  const validFrom = normalizeDateString(
    candidate.docs_next_valid_from ??
      progress.next_valid_from ??
      progress.valid_from ??
      progress.validFrom ??
      progress.timeline?.valid_from ??
      progress.timeline?.validFrom ??
      null,
  );

  const total = Number(progress.total ?? progress.count ?? 0) || 0;
  const readyCount = Number(progress.ready ?? progress.verified ?? progress.approved ?? 0) || 0;
  const problemCount =
    Number(progress.problem ?? progress.invalid ?? progress.expired ?? progress.overdue ?? 0) || 0;
  const inProgressCount =
    Number(progress.in_progress ?? progress.submitted ?? progress.pending_validation ?? 0) || 0;
  const orderedCount =
    Number(progress.ordered ?? progress.requested ?? progress.pending ?? progress.ordered_count ?? 0) || 0;
  const withFilesCount =
    Number(progress.with_files ?? progress.uploaded ?? progress.files ?? progress.files_count ?? 0) || 0;

  const hasFiles =
    typeof candidate.docs_has_files === 'boolean'
      ? candidate.docs_has_files
      : Boolean(withFilesCount > 0);

  const isOrdered =
    Boolean(orderedAt) ||
    Boolean(orderedCount > 0) ||
    readiness === 'ordered' ||
    String(progress.latest_status || '').toLowerCase() === 'ordered';

  if (!readiness) {
    if (problemCount > 0) readiness = 'problem';
    else if (readyCount > 0 && readyCount >= (total || readyCount)) readiness = 'ready';
    else if (inProgressCount > 0) readiness = 'in_progress';
    else if (isOrdered) readiness = 'ordered';
    else if (hasFiles || withFilesCount > 0) readiness = 'awaiting_review';
    else if (total > 0) readiness = 'pending';
    else readiness = 'pending';
  }

  const meta = DOC_READINESS_META[readiness] ?? DOC_READINESS_META.pending;
  const rank =
    typeof candidate.docs_readiness_rank === 'number'
      ? candidate.docs_readiness_rank
      : DOC_READINESS_ORDER[readiness] ?? 0;

  return {
    readinessState: readiness,
    readinessLabelKey: meta.labelKey,
    readinessClass: meta.className,
    readinessKey: readiness,
    rank,
    orderDate: orderedAt,
    orderTs: toTimestamp(orderedAt),
    validFrom: validFrom,
    validTs: toTimestamp(validFrom),
    hasFiles,
    isOrdered,
  };
}

export function normalizeCandidateExtra(raw: any): CandidateExtraNormalized {
  const extra = extractExtraObject(raw);
  const asString = (value: any): string | null => {
    if (typeof value !== 'string') return null;
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  };
  const toBool = (value: any): boolean | null => {
    if (value === true) return true;
    if (value === false) return false;
    if (typeof value === 'string') {
      const normalized = value.trim().toLowerCase();
      if (normalized === 'true' || normalized === 'yes') return true;
      if (normalized === 'false' || normalized === 'no') return false;
    }
    if (typeof value === 'number') {
      if (value === 1) return true;
      if (value === 0) return false;
    }
    return null;
  };
  const arrayOfStrings = (value: any): string[] => {
    if (!value) return [];
    if (Array.isArray(value)) {
      return value.map((item) => String(item).trim()).filter((item) => item.length > 0);
    }
    if (typeof value === 'string') {
      if (!value.trim()) return [];
      try {
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed)) {
          return parsed.map((item) => String(item).trim()).filter((item) => item.length > 0);
        }
      } catch {
        return value
          .split(',')
          .map((piece) => piece.trim())
          .filter((piece) => piece.length > 0);
      }
    }
    return [];
  };
  const normalizeOpsMode = (value: any): CandidateExtraNormalized['opsMode'] => {
    const rawValue = typeof value === 'string' ? value.trim().toLowerCase() : '';
    if (rawValue === 'in_work' || rawValue === 'later' || rawValue === 'no_reply_needed' || rawValue === 'escalated') {
      return rawValue;
    }
    return null;
  };

  return {
    citizenship: asString(extra.citizenship ?? extra.passport_country) ?? null,
    preferredContact: asString(extra.preferred_contact) ?? null,
    firstContactAt: asString(extra.first_contact_at) ?? null,
    inPoland: toBool(extra.in_poland),
    polandStayBasis: asString(extra.poland_stay_basis) ?? null,
    trailerTypes: arrayOfStrings(extra.trailer_types),
    opsMode: normalizeOpsMode(extra?.candidate_ops?.mode),
  };
}

export function getCandidateVacancyId(candidate: UICandidate): string | null {
  const raw =
    (candidate as any)?.vacancy_id ??
    (candidate as any)?.vacancy?.id ??
    (candidate as any)?.vacancy_uuid ??
    null;
  if (!raw) return null;
  const value = String(raw);
  return value && value !== 'null' ? value : null;
}

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isUuidLike(value: unknown): boolean {
  return typeof value === 'string' && UUID_RE.test(value.trim());
}

/**
 * Canonical assignee (Phase 2.6.G-5 Stage F).
 *
 * Reads `candidate.recruiter_id` first, then falls back to the legacy
 * `manager_id` / `manager` / `manager.id` shapes. Stage D shadow-write
 * keeps the two columns in sync, so in production the fallback only
 * matters during deploy interleave when one endpoint may have returned
 * a Stage-F payload and another a legacy one.
 *
 * This is the preferred helper — route ALL new code through here
 * instead of reading `candidate.manager` directly.
 */
export function getCandidateRecruiterId(candidate: UICandidate): string | null {
  const rid = (candidate as any)?.recruiter_id;
  if (rid != null && isUuidLike(rid)) return String(rid).trim();
  const mid = (candidate as any)?.manager_id;
  if (mid != null && isUuidLike(mid)) return String(mid).trim();
  const mobj = (candidate as any)?.manager;
  if (mobj && typeof mobj === 'object' && mobj.id != null && isUuidLike(mobj.id)) {
    return String(mobj.id).trim();
  }
  if (typeof mobj === 'string' && isUuidLike(mobj)) return mobj.trim();
  return null;
}

/**
 * Legacy alias for {@link getCandidateRecruiterId}. Kept for BC while
 * Stage F migration touches every call-site; remove together with
 * `candidates.manager` column in Stage G.
 *
 * Historically read `manager` first; post-Stage-F it defers to
 * `recruiter_id` so BOTH legacy and canonical reads resolve to the
 * same value.
 */
export function getCandidateManagerId(candidate: UICandidate): string | null {
  return getCandidateRecruiterId(candidate);
}
