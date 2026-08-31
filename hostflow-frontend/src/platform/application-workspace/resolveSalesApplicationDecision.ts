import type { Application } from '../../api/types/application'
import type { ObjectDecision } from '../decision-model/types'
import { clientDetailPath } from '../../services/platformHandoff'

type ExistingClientHint = {
  company_id: string
  name: string
  client_account_id?: string
}

export function existingClientFromApplication(application: Application): ExistingClientHint | null {
  const raw = application.extensions?.existing_client
  if (!raw || typeof raw !== 'object') return null
  const row = raw as Record<string, unknown>
  const companyId = String(row.company_id || '').trim()
  if (!companyId) return null
  const accountId = String(row.client_account_id || '').trim()
  return {
    company_id: companyId,
    name: String(row.name || '').trim() || application.title,
    client_account_id: accountId || undefined,
  }
}

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
                  label: t('app.sales_inquiry.workspace.call'),
                  href: `tel:${contactPhone.replace(/\s/g, '')}`,
                  variant: 'primary' as const,
                  icon: 'phone' as const,
                },
              ]
            : []),
        ]
      : undefined

  const existingClient = existingClientFromApplication(application)
  const existingHref = existingClient ? clientDetailPath(existingClient.company_id) : undefined

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
          ? t('app.sales_inquiry.closed', { defaultValue: 'Запрос закрыт' })
          : t('app.sales_inquiry.completed', { defaultValue: 'Обращение завершено' }),
      why: t('app.sales_inquiry.reopen_why', {
        defaultValue: 'Можно только сменить этап — например, если компания заинтересована позже.',
      }),
      primaryAction: null,
      secondaryActions:
        application.status === 'rejected'
          ? [
              {
                id: 'interested_later',
                label: t('app.sales_inquiry.interested_later', { defaultValue: 'Заинтересован, но позже' }),
                onClick: () => void onStage('qualified'),
                disabled,
              },
              {
                id: 'reopen',
                label: t('app.sales_inquiry.reopen', { defaultValue: 'Вернуть в работу' }),
                onClick: () => void onStage('contacted'),
                disabled,
              },
            ]
          : undefined,
      requiredContext: ['workflow', 'contacts', 'summary', 'history'],
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

  if (activeStep >= 3 && existingClient && existingHref) {
    return {
      stateId: 'sales.existing_client',
      currentState: t('app.sales_inquiry.step.existing_client_title', {
        defaultValue: 'Клиент уже есть',
      }),
      why: t('app.sales_inquiry.step.existing_client_body', {
        defaultValue: '«{{name}}» уже в клиентах. Не создавайте дубль — откройте карточку и добавьте услугу.',
        values: { name: existingClient.name },
      }),
      primaryAction: {
        id: 'open_existing_client',
        label: t('app.client_inquiry.service_order.open_client', { defaultValue: 'Открыть карточку клиента' }),
        href: existingHref,
      },
      secondaryActions: [
        {
          id: 'link_existing',
          label: converting
            ? t('app.sales_inquiry.linking', { defaultValue: 'Привязываем…' })
            : t('app.sales_inquiry.link_existing', { defaultValue: 'Привязать обращение' }),
          onClick: () => void onConvert(),
          disabled,
        },
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
      requiredContext: ['workflow', 'contacts', 'summary', 'history'],
      variant: 'success',
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
        label: converting ? t('app.leads.client_detail.creating') : t('app.leads.client_detail.create_client'),
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
      requiredContext: ['workflow', 'contacts', 'summary', 'history'],
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
        label: t('app.sales_inquiry.interested'),
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
      requiredContext: ['workflow', 'contacts', 'summary', 'history'],
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
          label: t('app.sales_inquiry.called'),
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
    requiredContext: ['workflow', 'contacts', 'summary', 'history'],
    afterActionHint: contactPhone
      ? t('app.sales_inquiry.after_call_hint', { defaultValue: 'После звонка отметьте «Позвонил».' })
      : undefined,
  }
}
