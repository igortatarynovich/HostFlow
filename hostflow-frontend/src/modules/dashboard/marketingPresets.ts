/** Overview Marketing presets — group Meta/Acquisition campaigns by name heuristics. */

export type MarketingCampaignPresetId =
  | 'drivers_poltrakt'
  | 'warehouse'
  | 'dispatcher'
  | 'ru'
  | 'agency'
  | 'eng'

export type MarketingCampaignPreset = {
  id: MarketingCampaignPresetId
  /** Case-insensitive substrings; match if ANY hits and NONE of exclude hits. */
  include: string[]
  exclude?: string[]
}

export const MARKETING_CAMPAIGN_PRESETS: MarketingCampaignPreset[] = [
  {
    id: 'drivers_poltrakt',
    include: ['driver', 'drivers', 'ce pol', 'italy', 'c+e', 'ce pl', 'week/cadence', 'kierowca'],
    exclude: ['magazyn', 'dyspozytor', 'agency', 'mrozek'],
  },
  {
    id: 'warehouse',
    include: ['magazyn'],
  },
  {
    id: 'dispatcher',
    include: ['dyspozytor'],
  },
  {
    id: 'ru',
    include: ['ru ', 'ru leads', 'mrozek', ' leads ru'],
  },
  {
    id: 'agency',
    include: ['agency'],
  },
  {
    id: 'eng',
    include: ['eng '],
  },
]

export function campaignMatchesPreset(name: string, preset: MarketingCampaignPreset): boolean {
  const n = ` ${String(name || '').toLowerCase()} `
  if (preset.exclude?.some((ex) => n.includes(ex.toLowerCase()))) return false
  return preset.include.some((inc) => n.includes(inc.toLowerCase()))
}

export function campaignIdsForPreset(
  campaigns: { campaign_id: string; name: string }[],
  presetId: MarketingCampaignPresetId,
): string[] {
  const preset = MARKETING_CAMPAIGN_PRESETS.find((p) => p.id === presetId)
  if (!preset) return []
  return campaigns.filter((c) => campaignMatchesPreset(c.name, preset)).map((c) => c.campaign_id)
}

/** Parse impressions/reach from import description marker. */
export function parseMetaAdsExtras(description?: string | null): {
  impressions: number | null
  reach: number | null
} {
  const d = String(description || '')
  if (!d.includes('[hf_meta_ads_import')) {
    return { impressions: null, reach: null }
  }
  const imp = d.match(/\bimpressions=(\d+)\b/i)
  const reach = d.match(/\breach=(\d+)\b/i)
  return {
    impressions: imp ? Number(imp[1]) : null,
    reach: reach ? Number(reach[1]) : null,
  }
}
