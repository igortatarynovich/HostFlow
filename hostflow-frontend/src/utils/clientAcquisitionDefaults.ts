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

export const CLIENT_AUDIENCE_OPTIONS: {
  id: ClientAudience
  emoji: string
  title: string
  subtitle: string
}[] = [
  { id: 'transport', emoji: '🚛', title: 'Транспортные компании', subtitle: 'Перевозчики, логистика, автопарки' },
  { id: 'manufacturing', emoji: '🏭', title: 'Производственные предприятия', subtitle: 'Заводы и производство' },
  { id: 'warehouse', emoji: '📦', title: 'Склады', subtitle: 'Логистические центры и склады' },
  { id: 'construction', emoji: '🏗️', title: 'Строительные компании', subtitle: 'Подрядчики и девелоперы' },
  { id: 'any', emoji: '🌐', title: 'Любой бизнес', subtitle: 'Универсальная страница заявки' },
]

export const CLIENT_SERVICE_OPTIONS: {
  id: ClientService
  title: string
}[] = [
  { id: 'driver_recruitment', title: 'Подбор водителей' },
  { id: 'warehouse_recruitment', title: 'Подбор складского персонала' },
  { id: 'office_recruitment', title: 'Подбор офисных сотрудников' },
  { id: 'outsourcing', title: 'Аутсорсинг' },
  { id: 'outstaffing', title: 'Аутстаффинг' },
  { id: 'other', title: 'Другое' },
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

  if (audience === 'transport' || hasDrivers) {
    return {
      headline: 'Нужны водители?',
      subheadline:
        'Мы помогаем транспортным компаниям находить проверенных водителей C+E и закрывать кадровые потребности быстрее.',
      cta: 'Оставить заявку',
    }
  }
  if (audience === 'warehouse' || hasWarehouse) {
    return {
      headline: 'Нужен персонал на склад?',
      subheadline: 'Подберём комплектовщиков, операторов погрузчиков и других сотрудников склада под ваши условия.',
      cta: 'Оставить заявку',
    }
  }
  if (hasOffice) {
    return {
      headline: 'Нужны сотрудники в офис?',
      subheadline: 'Поможем найти диспетчеров, менеджеров и других офисных специалистов для вашей компании.',
      cta: 'Оставить заявку',
    }
  }
  return {
    headline: 'Нужен персонал?',
    subheadline: 'Оставьте заявку — мы свяжемся с вами и предложим решение по подбору персонала.',
    cta: 'Оставить заявку',
  }
}

export function buildChannelName(audience: ClientAudience, services: ClientService[]): string {
  const audiencePart = audienceLabel(audience)
  const servicePart = services
    .slice(0, 2)
    .map((s) => CLIENT_SERVICE_OPTIONS.find((o) => o.id === s)?.title ?? s)
    .join(', ')
  return servicePart ? `Привлечение — ${audiencePart} (${servicePart})` : `Привлечение — ${audiencePart}`
}

export function slugifyChannel(audience: ClientAudience): string {
  const base = audience.replace(/_/g, '-')
  return `${base}-${Date.now().toString(36).slice(-5)}`
}
