import type { Application } from '../../api/types/application'
import { formAnswerRowsFromSources, type FormAnswerRow } from '../../utils/formAnswerRows'

export function applicationFormAnswerRows(application: Application): FormAnswerRow[] {
  const ext = application.extensions ?? {}
  return formAnswerRowsFromSources({
    fieldAnswers: ext.meta_form_answers,
    additionalAnswers: ext.additional_answers,
    labels: ext.form_question_labels_v1,
    contactFallback: {
      full_name: application.contact.name,
      phone: application.contact.phone ?? '',
      email: application.contact.email ?? '',
    },
  })
}
