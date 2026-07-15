import type { LeadSubmissionV1 } from './salesQuestionnaireSubmission'

export type SubmissionSourceV1 = {
  entry?: string | null
  invite_id?: string | null
}

export type SubmissionPolicySnapshot = {
  mode?: string | null
}

export type AttributionTranslate = (
  key: string,
  options?: { defaultValue?: string },
) => string

export type AttributionFormContext = {
  formTitle: string
  formId: string | null
  publicationName: string | null
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function text(value: unknown): string {
  if (value == null) return ''
  return String(value).trim()
}

export function normalizeLeadQuestionnaireFormsList(payload: unknown): unknown[] {
  if (Array.isArray(payload)) return payload
  const root = record(payload)
  for (const key of ['items', 'data', 'forms', 'results']) {
    const rows = root[key]
    if (Array.isArray(rows)) return rows
  }
  return []
}

export function questionnaireFormOptionId(row: unknown): string | null {
  const root = record(row)
  const nested = record(root.form)
  for (const candidate of [root.id, root.lead_form_id, root.form_id, nested.id]) {
    const id = text(candidate)
    if (id) return id
  }
  return null
}

export function questionnaireFormOptionTitle(row: unknown): string | null {
  const root = record(row)
  const nested = record(root.form)
  for (const candidate of [
    root.title,
    root.name,
    root.form_title,
    root.label,
    nested.title,
    nested.name,
  ]) {
    const title = text(candidate)
    if (title) return title
  }
  return null
}

export function findQuestionnaireFormTitleInList(rows: unknown[], formId: string): string | null {
  const needle = text(formId)
  if (!needle) return null
  for (const row of rows) {
    if (questionnaireFormOptionId(row) !== needle) continue
    const title = questionnaireFormOptionTitle(row)
    if (title) return title
  }
  return null
}

export function readIntakeFormDetailTitle(detail: unknown): string | null {
  const root = record(detail)
  const form = record(root.form)
  return text(form.title) || text(root.title) || null
}

export function readIntakeFormDetailPublicationName(detail: unknown): string | null {
  const root = record(detail)
  const profile = record(root.intake_source_profile)
  return text(profile.name) || null
}

export async function resolveAttributionFormContext(
  formId: string | null,
  deps: {
    listForms: () => Promise<unknown>
    getFormDetail: (id: string) => Promise<unknown>
    listLeadForms?: () => Promise<unknown>
  },
): Promise<AttributionFormContext> {
  if (!formId) {
    return { formTitle: '—', formId: null, publicationName: null }
  }

  try {
    const listPayload = await deps.listForms()
    const titleFromList = findQuestionnaireFormTitleInList(normalizeLeadQuestionnaireFormsList(listPayload), formId)
    if (titleFromList) {
      return { formTitle: titleFromList, formId, publicationName: null }
    }
  } catch {
    // fall through to intake form detail
  }

  try {
    const detail = await deps.getFormDetail(formId)
    const titleFromDetail = readIntakeFormDetailTitle(detail)
    if (titleFromDetail) {
      return {
        formTitle: titleFromDetail,
        formId,
        publicationName: readIntakeFormDetailPublicationName(detail),
      }
    }
  } catch {
    // fall through to tenant lead-forms list
  }

  if (deps.listLeadForms) {
    try {
      const leadFormsPayload = await deps.listLeadForms()
      const titleFromLeadForms = findQuestionnaireFormTitleInList(
        normalizeLeadQuestionnaireFormsList(leadFormsPayload),
        formId,
      )
      if (titleFromLeadForms) {
        return { formTitle: titleFromLeadForms, formId, publicationName: null }
      }
    } catch {
      // fall through to emergency fallback
    }
  }

  return { formTitle: formId, formId, publicationName: null }
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

export function submissionEntryLabel(
  entry: string | null | undefined,
  t: AttributionTranslate,
): string {
  const code = text(entry).toLowerCase()
  if (code === 'questionnaire_invite') {
    return t('app.sales_questionnaire.attribution.entry.questionnaire_invite', {
      defaultValue: 'Personal questionnaire invite',
    })
  }
  if (code === 'public_intake' || code === 'public_form' || code === 'public_apply') {
    return t('app.sales_questionnaire.attribution.entry.public_form', {
      defaultValue: 'Public form',
    })
  }
  if (!code) return '—'
  return code.replace(/_/g, ' ')
}

export function submissionPolicyModeLabel(
  mode: string | null | undefined,
  t: AttributionTranslate,
): string {
  const code = text(mode).toLowerCase()
  if (code === 'attach') {
    return t('app.sales_questionnaire.attribution.policy.attach', {
      defaultValue: 'Added to this inquiry',
    })
  }
  if (code === 'create') {
    return t('app.sales_questionnaire.attribution.policy.create', {
      defaultValue: 'Created a new inquiry',
    })
  }
  if (code === 'match_or_create') {
    return t('app.sales_questionnaire.attribution.policy.match_or_create', {
      defaultValue: 'Matched or created inquiry',
    })
  }
  if (code === 'review') {
    return t('app.sales_questionnaire.attribution.policy.review', {
      defaultValue: 'Sent to review queue',
    })
  }
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
