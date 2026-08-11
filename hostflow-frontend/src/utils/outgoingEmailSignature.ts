/**
 * Plain-text outgoing email signature from the personal profile (cabinet).
 * Aligns with backend `resolve_outgoing_signature` — profile-only, no tenant team stubs.
 */
import type { UserOutgoingSignature } from '../api/types'
import { lookupScopedTranslation, type LocaleCode } from '../i18n'

function normalizeLocale(locale: string | null | undefined): LocaleCode {
  const code = String(locale || 'pl').trim().toLowerCase().slice(0, 2)
  if (code === 'en' || code === 'ru' || code === 'pl') return code
  return 'pl'
}

export function closingForLocale(locale: string | null | undefined): string {
  const code = normalizeLocale(locale)
  return (
    lookupScopedTranslation(code, 'app.outgoing_signature', `closing_${code}`) ||
    (code === 'en' ? 'Kind regards,' : code === 'ru' ? 'Kind regards,' : 'Z poważaniem,')
  )
}

function normalizeWebsiteDisplay(raw: string): string {
  return raw.replace(/^https?:\/\//i, '').replace(/^www\./i, '').replace(/\/$/, '')
}

export type FormatOutgoingSignatureInput = {
  signature?: UserOutgoingSignature | null
  fallbackFirstName?: string | null
  fallbackLastName?: string | null
  fallbackFullName?: string | null
  fallbackPosition?: string | null
  fallbackPhone?: string | null
  fallbackEmail?: string | null
  locale?: string | null
}

/**
 * Build the plain-text block appended under `--` in inbox compose.
 * Returns '' when there is nothing meaningful to show (caller should skip append).
 */
export function formatOutgoingSignaturePlain(input: FormatOutgoingSignatureInput): string {
  const sig = input.signature || {}
  const closing = closingForLocale(input.locale)
  const first = String(sig.first_name || '').trim()
  const last = String(sig.last_name || '').trim()
  const fromSig = [first, last].filter(Boolean).join(' ')
  const fallbackName =
    String(input.fallbackFullName || '').trim() ||
    [String(input.fallbackFirstName || '').trim(), String(input.fallbackLastName || '').trim()]
      .filter(Boolean)
      .join(' ')
  const name = fromSig || fallbackName
  const position = String(sig.position || '').trim() || String(input.fallbackPosition || '').trim()
  const company = String(sig.company || '').trim()
  const phone = String(sig.phone || '').trim() || String(input.fallbackPhone || '').trim()
  const email = String(sig.email || '').trim() || String(input.fallbackEmail || '').trim()
  const websiteRaw = String(sig.website || '').trim()
  const website = websiteRaw ? normalizeWebsiteDisplay(websiteRaw) : ''
  const logo = String(sig.logo_url || '').trim()

  const lines: string[] = [closing, '']
  if (name) lines.push(name)
  if (position) lines.push(position)
  if (company) {
    lines.push('')
    lines.push(company)
  }
  const contacts: string[] = []
  if (sig.show_phone !== false && phone) contacts.push(`☎ ${phone}`)
  if (sig.show_email !== false && email) contacts.push(`✉ ${email}`)
  if (sig.show_website !== false && website) contacts.push(`↗ ${website}`)
  if (contacts.length) {
    lines.push('')
    lines.push(...contacts)
  }
  if (logo) {
    lines.push('')
    lines.push(logo)
  }

  const body = lines.join('\n').trim()
  // Closing alone is not a useful signature.
  if (!name && !position && !company && !contacts.length && !logo) return ''
  return body
}
