import type { LeadQuestionnaireFormOption } from '../api/client'

export const SALES_SERVICE_LABEL = 'Таргетированная реклама'

/** Primary questionnaire for a sales B2B workflow — system preset wins, else first active. */
export function pickPrimaryQuestionnaireForm(
  forms: LeadQuestionnaireFormOption[],
): LeadQuestionnaireFormOption | null {
  if (forms.length === 0) return null
  return forms.find((row) => row.is_system_preset) ?? forms[0]
}

export function shouldShowQuestionnairePicker(forms: LeadQuestionnaireFormOption[]): boolean {
  return forms.length > 1
}
