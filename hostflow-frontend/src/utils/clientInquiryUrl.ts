export function buildPublicClientInquiryUrl(publicSlug: string): string {
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  return `${origin}/forms/client-inquiry/${encodeURIComponent(publicSlug)}`
}

export function buildPublicClientInquiryApplyUrl(publicSlug: string): string {
  return `${buildPublicClientInquiryUrl(publicSlug)}/apply`
}

export { downloadQrPng } from './publicIntakeUrl'
