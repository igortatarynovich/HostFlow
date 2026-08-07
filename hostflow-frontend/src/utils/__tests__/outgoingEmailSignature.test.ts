import { describe, expect, it } from 'vitest'
import { closingForLocale, formatOutgoingSignaturePlain } from '../outgoingEmailSignature'

describe('outgoingEmailSignature', () => {
  it('uses pl closing by default', () => {
    expect(closingForLocale(undefined)).toBe('Z poważaniem,')
    expect(closingForLocale('pl-PL')).toBe('Z poważaniem,')
  })

  it('formats profile signature without recruitment team stub', () => {
    const text = formatOutgoingSignaturePlain({
      signature: {
        first_name: 'Anna',
        last_name: 'Kowalska',
        position: 'Account Manager',
        company: 'HostFlow Sales',
        phone: '+48111111111',
        email: 'anna@example.com',
        show_phone: true,
        show_email: true,
        show_website: false,
      },
      locale: 'pl',
    })
    expect(text).toContain('Z poważaniem,')
    expect(text).toContain('Anna Kowalska')
    expect(text).toContain('Account Manager')
    expect(text).toContain('HostFlow Sales')
    expect(text).toContain('☎ +48111111111')
    expect(text).toContain('✉ anna@example.com')
    expect(text).not.toContain('rekrutacji')
    expect(text).not.toContain('Zespół')
  })

  it('falls back to profile name/email when signature block is sparse', () => {
    const text = formatOutgoingSignaturePlain({
      signature: {},
      fallbackFirstName: 'Igor',
      fallbackLastName: 'T',
      fallbackEmail: 'igor@hostflow.cc',
      locale: 'en',
    })
    expect(text).toContain('Kind regards,')
    expect(text).toContain('Igor T')
    expect(text).toContain('✉ igor@hostflow.cc')
  })

  it('returns empty when nothing to show', () => {
    expect(formatOutgoingSignaturePlain({ signature: null, locale: 'pl' })).toBe('')
  })

  it('omits logo URL from plain-text signature', () => {
    const logo = 'https://recruitment.hostflow.cc/api/uploads/avatars/example.jpg'
    const text = formatOutgoingSignaturePlain({
      signature: {
        first_name: 'Igor',
        last_name: 'Tatarynovich',
        company: 'HostFlow',
        logo_url: logo,
        show_phone: false,
        show_email: false,
        show_website: false,
      },
      locale: 'ru',
    })
    expect(text).toContain('С уважением,')
    expect(text).toContain('Igor Tatarynovich')
    expect(text).not.toContain(logo)
    expect(text).not.toContain('https://')
  })
})
