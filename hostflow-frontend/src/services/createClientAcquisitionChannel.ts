import { listOwnCompanies } from '../api/client'
import { createCompanyIntakeSourceProfile } from '../api/companyIntakeSourceProfiles'
import {
  audienceLabel,
  buildChannelLanding,
  buildChannelName,
  slugifyChannel,
  type ClientAudience,
  type ClientChannelConfig,
  type ClientService,
} from '../utils/clientAcquisitionDefaults'
import { buildPublicClientInquiryUrl } from '../utils/clientInquiryUrl'

export type CreateClientAcquisitionChannelInput = {
  audience: ClientAudience
  services: ClientService[]
  serviceOtherLabel?: string
}

export type ClientAcquisitionChannelResult = {
  channelId: string
  name: string
  publicSlug: string
  publicUrl: string
  audience: ClientAudience
  services: ClientService[]
  channelConfig: ClientChannelConfig
}

export async function createClientAcquisitionChannel(
  input: CreateClientAcquisitionChannelInput,
): Promise<ClientAcquisitionChannelResult> {
  if (!input.services.length) throw new Error('services_required')

  const own = await listOwnCompanies()
  const ownCompanyId = own.items?.[0]?.id
  if (!ownCompanyId) throw new Error('own_company_missing')

  const landing = buildChannelLanding(input.audience, input.services)
  const channelConfig: ClientChannelConfig = {
    kind: 'client_channel_v1',
    audience: input.audience,
    services: input.services,
    service_other_label: input.serviceOtherLabel?.trim() || null,
    landing,
  }

  const publicSlug = slugifyChannel(input.audience)
  const profile = await createCompanyIntakeSourceProfile({
    name: buildChannelName(input.audience, input.services),
    own_company_id: String(ownCompanyId),
    public_slug: publicSlug,
    source: 'website',
    default_language: 'ru',
    supported_languages: ['ru', 'pl', 'en'],
    is_active: true,
    channel_config: channelConfig,
  })

  const slug = profile.public_slug || publicSlug
  return {
    channelId: profile.id,
    name: profile.name || buildChannelName(input.audience, input.services),
    publicSlug: slug,
    publicUrl: buildPublicClientInquiryUrl(slug),
    audience: input.audience,
    services: input.services,
    channelConfig,
  }
}

export function channelAudienceLabel(audience: ClientAudience): string {
  return audienceLabel(audience)
}
