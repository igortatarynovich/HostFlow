import type { Lead } from '../api/types'
import { formAnswerRowsFromSources, type FormAnswerRow } from './formAnswerRows'

export type LeadIntakeFormAnswerRow = FormAnswerRow

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

/** Meta / form answers — human question text, not field_code. */
export function leadIntakeFormAnswerRows(lead: Lead | null | undefined): FormAnswerRow[] {
  const n = asRecord(lead?.normalized)
  return formAnswerRowsFromSources({
    fieldAnswers: n?.field_answers,
    additionalAnswers: n?.additional_answers,
    labels: n?.form_question_labels_v1,
    payload: lead?.payload,
    contactFallback: n,
  })
}
