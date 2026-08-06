import type { Application } from '../../api/types/application'
import type { TranslateFn } from '../../i18n'
import type { ObjectDecision } from '../decision-model/types'
import { clientDetailPath } from '../../services/platformHandoff'

type ResolveSalesDecisionArgs = {
  application: Application
  converting: boolean
  patching: boolean
  onStage: (stage: 'contacted' | 'qualified' | 'lost') => void | Promise<void>
  onConvert: () => void | Promise<void>
  t: TranslateFn
}

export function resolveSalesApplicationDecision(args: ResolveSalesDecisionArgs): ObjectDecision {
  const { application, converting, patching, onStage, onConvert, t } = args
  const activeStep = Number(application.extensions?.workflow_step ?? 1)
  const convertedId = String(application.outcome_entity_id || '').trim()
  const clientHref = convertedId ? clientDetailPath(convertedId) : undefined
  const terminal = application.status === 'rejected' || application.status === 'completed'
  const contactPhone = application.contact.phone
  const disabled = patching || converting
  const closeLabel = t('app.sales_inquiry.close', { defaultValue: 'Close inquiry' })
  const laterLabel = t('app.sales_inquiry.interested_later', { defaultValue: 'Interested, but later' })

  const contactActions =
    !terminal && (contactPhone || application.contact.email)
      ? [
          ...(contactPhone
            ? [
                {
                  id: 'call',
                  label: t('app.sales_inquiry.call', { defaultValue: 'Call' }),
                  href: `tel:${contactPhone.replace(/\s/g, '')}`,
                  variant: 'primary' as const,
                  icon: 'phone' as const,
                },
              ]
            : []),
        ]
      : undefined

  if (convertedId && clientHref) {
    return {
      stateId: 'sales.client_created',
      currentState: t('app.sales_inquiry.step.service_title', { defaultValue: 'Add a service' }),
      why: t('app.sales_inquiry.step.service_body', {
        defaultValue: 'Client created. Open the card and add the first service.',
      }),
      primaryAction: {
        id: 'open_client',
        label: t('app.client_inquiry.service_order.open_client', {
          defaultValue: t('app.sales_inquiry.open_client_card', { defaultValue: 'Open client card' }),
        }),
        href: clientHref,
      },
      requiredContext: ['workflow', 'contacts', 'summary', 'history'],
      terminal: false,
      variant: 'success',
    }
  }

  if (terminal) {
    return {
      stateId: 'sales.terminal',
      currentState:
        application.status === 'rejected'
          ? t('app.sales_inquiry.closed', { defaultValue: 'Inquiry closed' })
          : t('app.sales_inquiry.completed', { defaultValue: 'Inquiry completed' }),
      why: undefined,
      primaryAction: null,
      requiredContext: ['workflow', 'contacts', 'summary', 'history'],
      terminal: true,
      outcome: {
        title:
          application.status === 'rejected'
            ? t('app.sales_inquiry.closed', { defaultValue: 'Inquiry closed' })
            : t('app.sales_inquiry.completed', { defaultValue: 'Inquiry completed' }),
        variant: 'terminal',
      },
    }
  }

  if (activeStep >= 3) {
    return {
      stateId: 'sales.create_client',
      currentState: t('app.sales_inquiry.step.client_title', { defaultValue: 'Create client' }),
      why: t('app.sales_inquiry.step.client_body', {
        defaultValue: 'The company is interested. Save it as a client.',
      }),
      primaryAction: {
        id: 'convert',
        label: converting
          ? t('app.sales_inquiry.creating', { defaultValue: 'Creating…' })
          : t('app.sales_inquiry.create_client', { defaultValue: 'Create client' }),
        onClick: () => void onConvert(),
        disabled,
      },
      secondaryActions: [
        {
          id: 'interested_later',
          label: laterLabel,
          onClick: () => void onStage('qualified'),
          disabled,
        },
        {
          id: 'close',
          label: closeLabel,
          onClick: () => void onStage('lost'),
          variant: 'danger',
          disabled,
        },
      ],
      contactActions,
      requiredContext: ['workflow', 'contacts', 'summary', 'history'],
      variant: 'default',
    }
  }

  if (activeStep >= 2) {
    return {
      stateId: 'sales.qualify_need',
      currentState: t('app.sales_inquiry.step.need_title', { defaultValue: 'Clarify the need' }),
      why: t('app.sales_inquiry.step.need_body', {
        defaultValue: 'Confirm which service the company wants to buy.',
      }),
      primaryAction: {
        id: 'qualified',
        label: t('app.sales_inquiry.interested', { defaultValue: 'Interested' }),
        onClick: () => void onStage('qualified'),
        disabled,
      },
      secondaryActions: [
        {
          id: 'interested_later',
          label: laterLabel,
          onClick: () => void onStage('qualified'),
          disabled,
        },
        {
          id: 'close',
          label: closeLabel,
          onClick: () => void onStage('lost'),
          variant: 'danger',
          disabled,
        },
      ],
      contactActions,
      requiredContext: ['workflow', 'contacts', 'summary', 'history'],
    }
  }

  return {
    stateId: 'sales.first_contact',
    currentState: t('app.sales_inquiry.step.contact_title', { defaultValue: 'Contact the client' }),
    why: t('app.sales_inquiry.step.contact_body', {
      defaultValue: 'First contact has not been made yet.',
    }),
    primaryAction: contactPhone
      ? {
          id: 'contacted',
          label: t('app.sales_inquiry.called', { defaultValue: 'Called' }),
          onClick: () => void onStage('contacted'),
          disabled,
        }
      : null,
    secondaryActions: [
      {
        id: 'close',
        label: closeLabel,
        onClick: () => void onStage('lost'),
        variant: 'danger',
        disabled,
      },
    ],
    contactActions,
    requiredContext: ['workflow', 'contacts', 'summary', 'history'],
    afterActionHint: contactPhone
      ? t('app.sales_inquiry.after_call_hint', { defaultValue: 'After the call, mark “Called”.' })
      : undefined,
  }
}
