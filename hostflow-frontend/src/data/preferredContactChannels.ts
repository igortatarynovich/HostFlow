export const PREFERRED_CONTACT_VALUES = ['', 'phone', 'viber', 'whatsapp', 'telegram'] as const
export type PreferredContactValue = typeof PREFERRED_CONTACT_VALUES[number]
