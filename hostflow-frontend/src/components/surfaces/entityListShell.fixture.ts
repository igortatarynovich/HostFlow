import type { EntityListDefinition } from './entityListTypes'

/** Fixture row shape for Phase 2A demo (vacancy-like, not wired to API). */
export type EntityListDemoRow = {
  id: string
  title: string
  companyName: string
  status: string
  candidateCount: number
}

export const ENTITY_LIST_DEMO_DEFINITION: EntityListDefinition<EntityListDemoRow> = {
  resourceId: 'vacancies-demo',
  density: 'comfortable',
  columns: [
    { id: 'title', fieldId: 'title', kind: 'text', label: 'Title', sortable: true },
    { id: 'company', fieldId: 'company_id', kind: 'ref', label: 'Company', sortable: true },
    { id: 'status', fieldId: 'status', kind: 'enum', label: 'Status', sortable: true },
    { id: 'candidates', fieldId: 'candidate_count', kind: 'number', label: 'Candidates' },
  ],
  filters: [
    { id: 'status', fieldId: 'status', kind: 'enum', label: 'Status' },
    { id: 'company', fieldId: 'company_id', kind: 'ref', label: 'Company' },
  ],
}

export const ENTITY_LIST_DEMO_ROWS: EntityListDemoRow[] = [
  { id: 'v1', title: 'Warehouse operator', companyName: 'LogiTrans Sp. z o.o.', status: 'open', candidateCount: 4 },
  { id: 'v2', title: 'Forklift driver', companyName: 'FreshFood PL', status: 'open', candidateCount: 2 },
  { id: 'v3', title: 'Production line', companyName: 'MetalWorks EU', status: 'paused', candidateCount: 0 },
  { id: 'v4', title: 'Night shift packer', companyName: 'LogiTrans Sp. z o.o.', status: 'closed', candidateCount: 8 },
  { id: 'v5', title: 'QC inspector', companyName: 'FreshFood PL', status: 'open', candidateCount: 1 },
  { id: 'v6', title: 'Driver CE', companyName: 'RoadFleet GmbH', status: 'open', candidateCount: 3 },
  { id: 'v7', title: 'Assembler', companyName: 'MetalWorks EU', status: 'draft', candidateCount: 0 },
  { id: 'v8', title: 'Seasonal picker', companyName: 'AgroPack S.A.', status: 'open', candidateCount: 5 },
]
