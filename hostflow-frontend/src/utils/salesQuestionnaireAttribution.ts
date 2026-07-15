import type { LeadSubmissionV1 } from './salesQuestionnaireSubmission'

export type SubmissionSourceV1 = {
  entry?: string | null
  invite_id?: string | null
}

export type SubmissionPolicySnapshot = {
  mode?: string | null
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

export function readSubmissionSource(submission: LeadSubmissionV1 | null): SubmissionSourceV1 {
  const raw = record(submission?.source)
  return {
    entry: text(raw.entry) || null,
    invite_id: text(raw.invite_id || submission?.invite_id) || null,
  }
}

export function readSubmissionPolicyMode(submission: LeadSubmissionV1 | null): string | null {
  const effective = record(submission?.effective_submission_policy)
  const policy = record(effective.submission_policy)
  const mode = text(policy.mode)
  return mode || null
}

export function submissionEntryLabel(entry: string | null | undefined): string {
  const code = text(entry).toLowerCase()
  if (code === 'questionnaire_invite') return 'Personal questionnaire invite'
  if (code === 'public_intake' || code === 'public_form' || code === 'public_apply') return 'Public form'
  if (!code) return '—'
  return code.replace(/_/g, ' ')
}

export function submissionPolicyModeLabel(mode: string | null | undefined): string {
  const code = text(mode).toLowerCase()
  if (code === 'attach') return 'Added to this inquiry'
  if (code === 'create') return 'Created a new inquiry'
  if (code === 'match_or_create') return 'Matched or created inquiry'
  if (code === 'review') return 'Sent to review queue'
  if (!code) return '—'
  return code.replace(/_/g, ' ')
}

export function shortId(value: string | null | undefined, keep = 8): string {
  const raw = text(value)
  if (!raw) return '—'
  if (raw.length <= keep * 2 + 1) return raw
  return `${raw.slice(0, keep)}…`
}

export function readSubmissionPublicationId(submission: LeadSubmissionV1 | null): string | null {
  const publicationId = text(submission?.publication_id)
  return publicationId || null
}

export function readSubmissionPurpose(submission: LeadSubmissionV1 | null): string | null {
  const purpose = text(submission?.purpose)
  return purpose || null
}

export function readSubmissionPublishedVersion(submission: LeadSubmissionV1 | null): number | null {
  const raw = submission?.published_version
  if (typeof raw === 'number' && Number.isFinite(raw)) return raw
  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : null
}
