import type { EntityModel, EntityPassport } from '../../entity-model'
import { entityField } from '../../entity-model'

/** Platform-only mocks — no module imports. For harness and tests. */

export const MOCK_CANDIDATE_MODEL: EntityModel = {
  resourceId: 'candidates',
  sections: ['identity', 'state', 'outcome', 'ownership', 'contacts', 'tasks', 'documents', 'timeline', 'relations', 'actions'],
  fields: [
    entityField({ id: 'name', label: 'Name', kind: 'text', section: 'identity', projection: { showInTable: true } }),
    entityField({ id: 'stage', label: 'Stage', kind: 'enum', section: 'state', projection: { showInEntitySummary: true } }),
  ],
}

export const MOCK_CLIENT_MODEL: EntityModel = {
  resourceId: 'clients',
  sections: ['identity', 'state', 'ownership', 'contacts', 'documents', 'timeline', 'relations', 'tasks', 'actions'],
  fields: [
    entityField({ id: 'company', label: 'Company', kind: 'text', section: 'identity', projection: { showInTable: true } }),
  ],
}

export const MOCK_ORDER_MODEL: EntityModel = {
  resourceId: 'service_orders',
  sections: ['identity', 'state', 'outcome', 'ownership', 'contacts', 'documents', 'timeline', 'relations', 'tasks', 'actions'],
  fields: [
    entityField({ id: 'order_no', label: 'Order', kind: 'text', section: 'identity', projection: { showInTable: true } }),
  ],
}

export const MOCK_CANDIDATE_PASSPORT: EntityPassport = {
  resourceId: 'candidates',
  entityId: 'mock-candidate-1',
  sections: {
    identity: { title: 'Jan Kowalski', shortId: '1042' },
    state: {
      phaseId: 'candidate.docs',
      processPhase: 'active',
      processLabel: 'Собрать документы',
      stageLabel: 'Ожидание документов',
      recruiterWorkActive: true,
      why: 'Не хватает карты пobyту',
    },
    outcome: null,
    ownership: { managerLabel: 'Anna Recruiter' },
    contacts: {
      displayName: 'Jan Kowalski',
      channels: [{ kind: 'phone', value: '+48 600 000 000', href: 'tel:+48600000000', primary: true }],
    },
    tasks: {
      items: [{ id: 't1', title: 'Запросить скан паспорта', dueAt: '2026-07-10', overdue: true }],
      nextTaskId: 't1',
    },
    documents: {
      readinessLabel: 'awaiting_review',
      blockersSummary: 'Не хватает: karta_pobytu',
      missing: ['karta_pobytu'],
      problematic: [],
      inProgress: ['passport'],
    },
    timeline: {
      items: [
        { id: 'e1', at: '2026-07-08', title: 'Первый звонок', description: 'Кандидат заинтересован' },
        { id: 'e2', at: '2026-07-07', title: 'Отклик получен' },
      ],
    },
    relations: {
      items: [{ id: 'v1', kind: 'vacancy', label: 'Driver CE — Berlin', entityId: 'vac-1' }],
    },
    actions: {
      workAllowed: true,
      capabilities: [{ id: 'request_documents', allowed: true, primary: true }],
      primaryCapabilityId: 'request_documents',
      decisionTitle: 'Запросить документы',
      decisionWhy: 'Не хватает карты pobyту',
    },
  },
}

export const MOCK_CLIENT_PASSPORT: EntityPassport = {
  resourceId: 'clients',
  entityId: 'mock-client-1',
  sections: {
    identity: { title: 'TransLog GmbH', shortId: 'CL-88' },
    state: {
      phaseId: 'client.active',
      processPhase: 'active',
      processLabel: 'Активный клиент',
      stageLabel: 'В работе',
      recruiterWorkActive: false,
    },
    outcome: null,
    ownership: { managerLabel: 'Sales Manager' },
    contacts: {
      displayName: 'TransLog GmbH',
      channels: [{ kind: 'email', value: 'ops@translog.de', href: 'mailto:ops@translog.de' }],
    },
    tasks: { items: [] },
    documents: { missing: [], problematic: [], inProgress: [] },
    timeline: {
      items: [{ id: 'e1', at: '2026-06-01', title: 'Клиент создан' }],
    },
    relations: {
      items: [{ id: 'o1', kind: 'other', label: 'Заказ #SO-441', entityId: 'order-1' }],
    },
    actions: {
      workAllowed: true,
      capabilities: [],
      decisionTitle: 'Добавить услугу',
      decisionWhy: 'Нет активного заказа',
    },
  },
}

export const MOCK_ORDER_PASSPORT: EntityPassport = {
  resourceId: 'service_orders',
  entityId: 'mock-order-1',
  sections: {
    identity: { title: 'Заказ SO-441', shortId: 'SO-441' },
    state: {
      phaseId: 'order.completed',
      processPhase: 'terminal',
      processLabel: 'Заказ выполнен',
      stageLabel: 'Закрыт',
      recruiterWorkActive: false,
    },
    outcome: {
      title: 'Заказ закрыт',
      body: 'Услуга оказана, счёт оплачен.',
      variant: 'success',
      whenLabel: '2026-07-01',
    },
    ownership: { managerLabel: 'Operations' },
    contacts: { channels: [] },
    tasks: { items: [] },
    documents: { missing: [], problematic: [], inProgress: [] },
    timeline: {
      items: [{ id: 'e1', at: '2026-07-01', title: 'Заказ закрыт' }],
    },
    relations: {
      items: [{ id: 'c1', kind: 'client', label: 'TransLog GmbH', entityId: 'mock-client-1' }],
    },
    actions: {
      workAllowed: false,
      capabilities: [],
      primaryCapabilityId: null,
    },
  },
}

export type EntityWorkspaceMockKey = 'candidate' | 'client' | 'order'

export const ENTITY_WORKSPACE_MOCKS: Record<
  EntityWorkspaceMockKey,
  { model: EntityModel; passport: EntityPassport; resourceTypeLabel: string }
> = {
  candidate: { model: MOCK_CANDIDATE_MODEL, passport: MOCK_CANDIDATE_PASSPORT, resourceTypeLabel: 'Кандидат' },
  client: { model: MOCK_CLIENT_MODEL, passport: MOCK_CLIENT_PASSPORT, resourceTypeLabel: 'Клиент' },
  order: { model: MOCK_ORDER_MODEL, passport: MOCK_ORDER_PASSPORT, resourceTypeLabel: 'Заказ' },
}
