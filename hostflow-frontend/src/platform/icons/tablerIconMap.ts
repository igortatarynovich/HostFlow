import type { Icon as TablerIcon } from '@tabler/icons-react'
import {
  IconBrandFacebook,
  IconBrandFacebookFilled,
  IconBrandGoogle,
  IconBrandGoogleFilled,
  IconBrandInstagram,
  IconBrandInstagramFilled,
  IconBrandLinkedin,
  IconBrandLinkedinFilled,
  IconBrandMeta,
  IconBrandTelegram,
  IconBrandTiktok,
  IconBrandTiktokFilled,
  IconBrandVk,
  IconBrandWhatsapp,
  IconBrandWhatsappFilled,
  IconBrandX,
  IconMail,
  IconMessage,
  IconPhone,
  IconUsers,
  IconWebhook,
  IconWorld,
} from '@tabler/icons-react'

export const TABLER_ICON_MAP: Record<string, TablerIcon> = {
  IconBrandWhatsapp,
  IconBrandWhatsappFilled,
  IconBrandTelegram,
  IconPhone,
  IconMail,
  IconMessage,
  IconBrandMeta,
  IconBrandFacebook,
  IconBrandFacebookFilled,
  IconBrandGoogle,
  IconBrandGoogleFilled,
  IconBrandTiktok,
  IconBrandTiktokFilled,
  IconBrandLinkedin,
  IconBrandLinkedinFilled,
  IconBrandInstagram,
  IconBrandInstagramFilled,
  IconBrandX,
  IconBrandVk,
  IconUsers,
  IconWorld,
  IconWebhook,
}

export function resolveTablerIcon(name: string | undefined): TablerIcon | undefined {
  if (!name) return undefined
  return TABLER_ICON_MAP[name]
}
