/**
 * Resolves operator communication menu from lead + workflow context.
 *
 * Capability / workflow is resolved here — never in the composer.
 * Composer receives only LeadCommunicationMenu.
 */

import type { LeadQuestionnaireFormOption } from '../api/client'
import type { ApplicationModule } from '../api/types/application'
import type { Lead } from '../api/types'
import type { CommunicationAction, LeadCommunicationMenu } from './communicationModel'
import { pickPrimaryQuestionnaireForm } from './communicationFormConstants'

/** Internal workflow key — not exposed to operator UI. */
type LeadWorkflowKey = 'sales.b2b.targeted_advertising' | 'recruitment.candidate'

type WorkflowMenuBuilder = (forms: LeadQuestionnaireFormOption[]) => Pick<
  LeadCommunicationMenu,
  'obtainInformation' | 'sendOutbound'
>

function questionnaireVariants(forms: LeadQuestionnaireFormOption[]) {
  return forms.map((form) => ({ id: form.id, label: form.title }))
}

const WORKFLOW_MENU_BUILDERS: Record<LeadWorkflowKey, WorkflowMenuBuilder> = {
  'sales.b2b.targeted_advertising': (forms) => {
    const primary = pickPrimaryQuestionnaireForm(forms)
    const variants = questionnaireVariants(forms)
    return {
      obtainInformation: [
        {
          id: 'fill_questionnaire',
          label: 'Заполнить анкету',
          enabled: Boolean(primary),
          attachmentKind: 'intake_form',
          variantPickerLabel: 'Анкета',
          variants,
          resolvedVariant: primary ? { id: primary.id, label: primary.title } : undefined,
        },
        {
          id: 'upload_documents',
          label: 'Прислать документы',
          enabled: false,
          attachmentKind: 'documents',
        },
        {
          id: 'send_photos',
          label: 'Прислать фотографии',
          enabled: false,
          attachmentKind: 'photos_videos',
        },
        {
          id: 'send_brief',
          label: 'Прислать бриф',
          enabled: false,
          attachmentKind: 'brief',
        },
      ],
      sendOutbound: [
        {
          id: 'send_proposal',
          label: 'Коммерческое предложение',
          enabled: false,
          attachmentKind: 'commercial_proposal',
        },
        {
          id: 'send_contract',
          label: 'Договор',
          enabled: false,
          attachmentKind: 'contract',
        },
        {
          id: 'send_invoice',
          label: 'Счёт',
          enabled: false,
          attachmentKind: 'invoice',
        },
      ],
    }
  },
  'recruitment.candidate': (forms) => {
    const primary = pickPrimaryQuestionnaireForm(forms)
    return {
      obtainInformation: [
        {
          id: 'fill_questionnaire',
          label: 'Заполнить анкету',
          enabled: Boolean(primary),
          attachmentKind: 'intake_form',
          variantPickerLabel: 'Анкета',
          variants: questionnaireVariants(forms),
          resolvedVariant: primary ? { id: primary.id, label: primary.title } : undefined,
        },
        {
          id: 'upload_documents',
          label: 'Прислать документы',
          enabled: false,
          attachmentKind: 'documents',
        },
        {
          id: 'send_photos',
          label: 'Прислать фотографии',
          enabled: false,
          attachmentKind: 'photos_videos',
        },
      ],
      sendOutbound: [],
    }
  },
}

function resolveLeadWorkflowKey(lead: Lead, module?: ApplicationModule): LeadWorkflowKey {
  if (module === 'sales') return 'sales.b2b.targeted_advertising'
  if (lead.lead_type === 'candidate' || lead.lead_target_type === 'candidate') {
    return 'recruitment.candidate'
  }
  if (lead.lead_target_type === 'client_lead' || lead.lead_target_type === 'service_order_lead') {
    return 'sales.b2b.targeted_advertising'
  }
  if (lead.business_type === 'services') return 'sales.b2b.targeted_advertising'
  return 'sales.b2b.targeted_advertising'
}

function buildPurposes(menu: Pick<LeadCommunicationMenu, 'obtainInformation' | 'sendOutbound'>) {
  const hasObtain = menu.obtainInformation.some((action) => action.enabled)
  const hasSend = menu.sendOutbound.some((action) => action.enabled)
  return [
    { id: 'write_message' as const, label: 'Написать сообщение', enabled: true },
    { id: 'obtain_information' as const, label: 'Получить информацию', enabled: hasObtain },
    { id: 'send_outbound' as const, label: 'Отправить', enabled: hasSend },
    { id: 'schedule_meeting' as const, label: 'Назначить встречу', enabled: false },
    { id: 'other' as const, label: 'Другое', enabled: false },
  ]
}

export function resolveLeadCommunicationMenu(args: {
  lead: Lead
  forms: LeadQuestionnaireFormOption[]
  module?: ApplicationModule
}): LeadCommunicationMenu {
  const workflowKey = resolveLeadWorkflowKey(args.lead, args.module)
  const builder = WORKFLOW_MENU_BUILDERS[workflowKey]
  const sections = builder(args.forms)
  return {
    ...sections,
    purposes: buildPurposes(sections),
  }
}

export function findQuestionnaireAction(menu: LeadCommunicationMenu): CommunicationAction | null {
  return menu.obtainInformation.find((action) => action.id === 'fill_questionnaire') || null
}
