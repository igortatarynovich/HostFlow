import type { SubmissionAnswerRow } from '../utils/salesQuestionnaireSubmissions'

export type AnswerFieldDiff = {
  key: string
  label: string
  previous: string
  next: string
}

export function diffAnswerRows(previous: SubmissionAnswerRow[], next: SubmissionAnswerRow[]): AnswerFieldDiff[] {
  const prevByCode = new Map(previous.map((row) => [row.qualifiedCode, row]))
  const diffs: AnswerFieldDiff[] = []
  for (const row of next) {
    const prior = prevByCode.get(row.qualifiedCode)
    if (!prior) {
      if (row.value.trim()) {
        diffs.push({ key: row.qualifiedCode, label: row.label, previous: '—', next: row.value })
      }
      continue
    }
    if (prior.value.trim() !== row.value.trim()) {
      diffs.push({
        key: row.qualifiedCode,
        label: row.label,
        previous: prior.value || '—',
        next: row.value || '—',
      })
    }
  }
  return diffs
}
