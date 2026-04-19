/** Canonical messenger channel keys for inbox integrations (aligned with API `channel`). */
export const MESSENGER_CHANNELS = ['telegram', 'whatsapp', 'viber', 'messenger', 'instagram'] as const

export type MessengerChannel = (typeof MESSENGER_CHANNELS)[number]

export function isMessengerChannel(value: string | undefined): value is MessengerChannel {
  return !!value && MESSENGER_CHANNELS.includes(value as MessengerChannel)
}
