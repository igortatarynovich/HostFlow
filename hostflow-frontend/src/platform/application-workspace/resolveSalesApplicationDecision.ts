import type { Application } from '../../api/types/application'
import type { ObjectDecision } from '../decision-model/types'
import { clientDetailPath } from '../../services/platformHandoff'

type ResolveSalesDecisionArgs = {
  application: Application
  converting: boolean
  patching: boolean
  onStage: (stage: 'contacted' | 'qualified' | 'lost') => void | Promise<void>
  onConvert: () => void | Promise<void>
  t: (key: string, options?: Record<string, unknown>) => string
}

export function resolveSalesApplicationDecision(args: ResolveSalesDecisionArgs): ObjectDecision {
  const { application, converting, patching, onStage, onConvert, t } = args
  const activeStep = Number(application.extensions?.workflow_step ?? 1)
  const convertedId = String(application.outcome_entity_id || '').trim()
  const clientHref = convertedId ? clientDetailPath(convertedId) : undefined
  const terminal = application.status === 'rejected' || application.status === 'completed'
  const contactPhone = application.contact.phone
  const disabled = patching || converting

  const contactActions =
    !terminal && (contactPhone || application.contact.email)
      ? [
          ...(contactPhone
            ? [
                {
                  id: 'call',
                  label: 'Позвонить',
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
      currentState: t('app.sales_inquiry.step.service_title', { defaultValue: 'Добавить услугу' }),
      why: t('app.sales_inquiry.step.service_body', {
        defaultValue: 'Клиент создан. Откройте карточку и добавьте первую услугу.',
      }),
      primaryAction: {
        id: 'open_client',
        label: t('app.client_inquiry.service_order.open_client', { defaultValue: 'Открыть карточку клиента' }),
        href: clientHref,
      },
      requiredContext: ['workflow', 'contacts', 'summary', 'relations', 'history'],
      terminal: false,
      variant: 'success',
    }
  }

  if (terminal) {
    return {
      stateId: 'sales.terminal',
      currentState:
        application.status === 'rejected'
          ? t('app.sales_inquiry.closed', { defaultValue: 'Запрос закрыт' })
          : t('app.sales_inquiry.completed', { defaultValue: 'Обращение завершено' }),
      why: undefined,
      primaryAction: null,
      requiredContext: ['workflow', 'contacts', 'relations', 'history'],
      terminal: true,
      outcome: {
        title:
          application.status === 'rejected'
            ? t('app.sales_inquiry.closed', { defaultValue: 'Запрос закрыт' })
            : t('app.sales_inquiry.completed', { defaultValue: 'Обращение завершено' }),
        variant: 'terminal',
      },
    }
  }

  if (application.status === 'waiting') {
    return {
      stateId: 'sales.awaiting_questionnaire',
      currentState: t('app.sales_inquiry.step.waiting_title', { defaultValue: 'Ожидаем ответ' }),
      why: t('app.sales_inquiry.step.waiting_body', {
        defaultValue: 'Анкета отправлена. Ждём, пока клиент заполнит и отправит ответы.',
      }),
      primaryAction: null,
      secondaryActions: [
        {
          id: 'close',
          label: t('app.sales_inquiry.close', { defaultValue: 'Закрыть запрос' }),
          onClick: () => void onStage('lost'),
          variant: 'danger',
          disabled,
        },
      ],
      contactActions,
      requiredContext: ['workflow', 'contacts', 'summary', 'relations', 'history'],
      variant: 'blocker',
    }
  }

  if (application.status === 'questionnaire_submitted') {
    return {
      stateId: 'sales.contact_after_questionnaire',
      currentState: t('app.sales_inquiry.step.contact_title', { defaultValue: 'Связаться с клиентом' }),
      why: t('app.sales_inquiry.step.questionnaire_filled_why', {
        defaultValue: 'Клиент заполнил анкету.',
      }),
      primaryAction: contactPhone
        ? {
            id: 'contacted',
            label: 'Позвонил',
            onClick: () => void onStage('contacted'),
            disabled,
          }
        : {
            id: 'convert',
            label: converting ? 'Создаём…' : 'Создать клиента',
            onClick: () => void onConvert(),
            disabled,
          },
      secondaryActions: [
        {
          id: 'interested_later',
          label: t('app.sales_inquiry.interested_later', { defaultValue: 'Заинтересован, но позже' }),
          onClick: () => void onStage('qualified'),
          disabled,
        },
        {
          id: 'close',
          label: t('app.sales_inquiry.close', { defaultValue: 'Закрыть запрос' }),
          onClick: () => void onStage('lost'),
          variant: 'danger',
          disabled,
        },
      ],
      contactActions,
      requiredContext: ['workflow', 'contacts', 'summary', 'relations', 'history'],
      afterActionHint: contactPhone
        ? t('app.sales_inquiry.after_call_hint', { defaultValue: 'После звонка отметьте «Позвонил».' })
        : undefined,
    }
  }

  if (activeStep >= 3) {
    return {
      stateId: 'sales.create_client',
      currentState: t('app.sales_inquiry.step.client_title', { defaultValue: 'Создать клиента' }),
      why: t('app.sales_inquiry.step.client_body', {
        defaultValue: 'Компания заинтересована. Сохраните её в клиенты.',
      }),
      primaryAction: {
        id: 'convert',
        label: converting ? 'Создаём…' : 'Создать клиента',
        onClick: () => void onConvert(),
        disabled,
      },
      secondaryActions: [
        {
          id: 'interested_later',
          label: t('app.sales_inquiry.interested_later', { defaultValue: 'Заинтересован, но позже' }),
          onClick: () => void onStage('qualified'),
          disabled,
        },
        {
          id: 'close',
          label: t('app.sales_inquiry.close', { defaultValue: 'Закрыть запрос' }),
          onClick: () => void onStage('lost'),
          variant: 'danger',
          disabled,
        },
      ],
      contactActions,
      requiredContext: ['workflow', 'contacts', 'summary', 'relations', 'history'],
      variant: 'default',
    }
  }

  if (activeStep >= 2) {
    return {
      stateId: 'sales.qualify_need',
      currentState: t('app.sales_inquiry.step.need_title', { defaultValue: 'Выяснить потребность' }),
      why: t('app.sales_inquiry.step.need_body', {
        defaultValue: 'Уточните, какую услугу компания хочет купить.',
      }),
      primaryAction: {
        id: 'qualified',
        label: 'Заинтересован',
        onClick: () => void onStage('qualified'),
        disabled,
      },
      secondaryActions: [
        {
          id: 'interested_later',
          label: t('app.sales_inquiry.interested_later', { defaultValue: 'Заинтересован, но позже' }),
          onClick: () => void onStage('qualified'),
          disabled,
        },
        {
          id: 'close',
          label: t('app.sales_inquiry.close', { defaultValue: 'Закрыть запрос' }),
          onClick: () => void onStage('lost'),
          variant: 'danger',
          disabled,
        },
      ],
      contactActions,
      requiredContext: ['workflow', 'contacts', 'summary', 'relations', 'history'],
    }
  }

  return {
    stateId: 'sales.first_contact',
    currentState: t('app.sales_inquiry.step.contact_title', { defaultValue: 'Связаться с клиентом' }),
    why: t('app.sales_inquiry.step.contact_body', {
      defaultValue: 'Первый контакт ещё не выполнен.',
    }),
    primaryAction: contactPhone
      ? {
          id: 'contacted',
          label: 'Позвонил',
          onClick: () => void onStage('contacted'),
          disabled,
        }
      : null,
    secondaryActions: [
      {
        id: 'close',
        label: t('app.sales_inquiry.close', { defaultValue: 'Закрыть запрос' }),
        onClick: () => void onStage('lost'),
        variant: 'danger',
        disabled,
      },
    ],
    contactActions,
    requiredContext: ['workflow', 'contacts', 'summary', 'relations', 'history'],
    afterActionHint: contactPhone
      ? t('app.sales_inquiry.after_call_hint', { defaultValue: 'После звонка отметьте «Позвонил».' })
      : undefined,
  }
}
