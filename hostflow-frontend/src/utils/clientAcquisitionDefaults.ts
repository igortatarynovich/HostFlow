export type ClientAudience =
  | 'transport'
  | 'manufacturing'
  | 'warehouse'
  | 'construction'
  | 'any'

export type ClientService =
  | 'driver_recruitment'
  | 'warehouse_recruitment'
  | 'office_recruitment'
  | 'outsourcing'
  | 'outstaffing'
  | 'other'

export type ClientChannelLanding = {
  headline: string
  subheadline: string
  cta: string
}

export type ClientChannelConfig = {
  kind: 'client_channel_v1'
  audience: ClientAudience
  services: ClientService[]
  service_other_label?: string | null
  landing: ClientChannelLanding
}

/** English catalog labels — UI should translate via `app.client_acquisition.*` keys. */
export const CLIENT_AUDIENCE_OPTIONS: {
  id: ClientAudience
  emoji: string
  title: string
  subtitle: string
}[] = [
  { id: 'transport', emoji: '🚛', title: 'Transport companies', subtitle: 'Carriers, logistics, fleets' },
  {
    id: 'manufacturing',
    emoji: '🏭',
    title: 'Manufacturing companies',
    subtitle: 'Factories and production',
  },
  { id: 'warehouse', emoji: '📦', title: 'Warehouses', subtitle: 'Logistics hubs and warehouses' },
  {
    id: 'construction',
    emoji: '🏗️',
    title: 'Construction companies',
    subtitle: 'Contractors and developers',
  },
  { id: 'any', emoji: '🌐', title: 'Any business', subtitle: 'Universal inquiry page' },
]

export const CLIENT_SERVICE_OPTIONS: {
  id: ClientService
  title: string
}[] = [
  { id: 'driver_recruitment', title: 'Driver recruitment' },
  { id: 'warehouse_recruitment', title: 'Warehouse staff recruitment' },
  { id: 'office_recruitment', title: 'Office staff recruitment' },
  { id: 'outsourcing', title: 'Outsourcing' },
  { id: 'outstaffing', title: 'Outstaffing' },
  { id: 'other', title: 'Other' },
]

export function audienceLabel(audience: ClientAudience): string {
  return CLIENT_AUDIENCE_OPTIONS.find((o) => o.id === audience)?.title ?? audience
}

export function buildChannelLanding(
  audience: ClientAudience,
  services: ClientService[],
): ClientChannelLanding {
  const hasDrivers = services.includes('driver_recruitment')
  const hasWarehouse = services.includes('warehouse_recruitment')
  const hasOffice = services.includes('office_recruitment')
  const cta = 'Submit inquiry'

  if (audience === 'transport' || hasDrivers) {
    return {
      headline: 'Need drivers?',
      subheadline:
        'We help transport companies find verified C+E drivers and close staffing needs faster.',
      cta,
    }
  }
  if (audience === 'warehouse' || hasWarehouse) {
    return {
      headline: 'Need warehouse staff?',
      subheadline:
        'We will find pickers, forklift operators and other warehouse roles for your conditions.',
      cta,
    }
  }
  if (hasOffice) {
    return {
      headline: 'Need office staff?',
      subheadline: 'We help find dispatchers, managers and other office specialists for your company.',
      cta,
    }
  }
  return {
    headline: 'Need staff?',
    subheadline: 'Submit an inquiry — we will contact you and propose a staffing solution.',
    cta,
  }
}

export function buildChannelName(audience: ClientAudience, services: ClientService[]): string {
  const audiencePart = audienceLabel(audience)
  const servicePart = services
    .slice(0, 2)
    .map((s) => CLIENT_SERVICE_OPTIONS.find((o) => o.id === s)?.title ?? s)
    .join(', ')
  return servicePart
    ? `Acquisition — ${audiencePart} (${servicePart})`
    : `Acquisition — ${audiencePart}`
}

export function slugifyChannel(audience: ClientAudience): string {
  const base = audience.replace(/_/g, '-')
  return `${base}-${Date.now().toString(36).slice(-5)}`
}
