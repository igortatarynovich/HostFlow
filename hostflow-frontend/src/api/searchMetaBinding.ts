import { api } from './client'

export type MetaSearchCampaign = {
  id: string
  name: string
  status?: string
  objective?: string
  ads_count?: number
  bound_to_search?: boolean
}

export type MetaSearchInventory = {
  connected: boolean
  page_id?: string | null
  ad_account_id?: string | null
  page_name?: string | null
  ad_account_name?: string | null
  campaigns: MetaSearchCampaign[]
  bound_campaign_ids?: string[]
  needs_marketing_reconnect?: boolean
  empty_message?: string | null
  warnings?: string[]
}

export type MetaSearchBindResult = {
  bound_ads: number
  bound_forms: number
  skipped: string[]
  inventory: MetaSearchInventory
}

export async function getSearchMetaInventory(searchId: string): Promise<MetaSearchInventory> {
  const { data } = await api.get<MetaSearchInventory>(`/vacancies/${encodeURIComponent(searchId)}/meta/inventory`)
  return data
}

export async function bindSearchMetaCampaigns(
  searchId: string,
  campaignIds: string[],
): Promise<MetaSearchBindResult> {
  const { data } = await api.post<MetaSearchBindResult>(
    `/vacancies/${encodeURIComponent(searchId)}/meta/bind-campaigns`,
    { campaign_ids: campaignIds },
  )
  return data
}
