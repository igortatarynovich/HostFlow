/**
 * Client preparation checklist — projection of company / orders / contacts /
 * invoices / contract markers. Mirrors `backend/app/services/client_preparation.py`.
 */

export type ClientPreparationItemStatus = 'done' | 'missing' | 'warning'

export interface ClientPreparationCheckItem {
  key: string
  status: ClientPreparationItemStatus
  soft: boolean
  visible: boolean
  title: string
  title_key?: string | null
  hint?: string | null
  hint_key?: string | null
  href?: string | null
}

export interface ClientPreparationChecklistDTO {
  entity_type: 'client'
  entity_id: string
  is_prepared: boolean
  items: ClientPreparationCheckItem[]
}
