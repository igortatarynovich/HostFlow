import {
  questionnaireInvitationTemplates,
  type QuestionnaireInvitationTemplates,
  type QuestionnaireMessageContext,
} from './questionnaireMessageTemplates'

export type CommunicationTemplatePurpose = 'obtain_information_questionnaire'

/**
 * Resolves outbound message templates for the composer.
 * Uses platform defaults; tenant overrides from settings API can be wired here later.
 */
export function resolveCommunicationTemplates(args: {
  purpose: CommunicationTemplatePurpose
  locale?: string
  context: QuestionnaireMessageContext
}): QuestionnaireInvitationTemplates {
  if (args.purpose === 'obtain_information_questionnaire') {
    return questionnaireInvitationTemplates(args.context, args.locale)
  }
  return questionnaireInvitationTemplates(args.context, args.locale)
}
