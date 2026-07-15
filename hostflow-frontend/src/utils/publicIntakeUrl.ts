export function buildPublicIntakeUrl(params: { leadFormSlug: string; vacancyId: string }): string {
  const q = new URLSearchParams({
    lead_form_slug: params.leadFormSlug,
    vacancy_id: params.vacancyId,
  })
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  return `${origin}/public/intake?${q.toString()}`
}

export async function downloadQrPng(url: string, filename: string): Promise<void> {
  const qrApi = `https://api.qrserver.com/v1/create-qr-code/?size=512x512&data=${encodeURIComponent(url)}`
  const res = await fetch(qrApi)
  if (!res.ok) throw new Error('qr_download_failed')
  const blob = await res.blob()
  const objectUrl = URL.createObjectURL(blob)
  try {
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = filename
    a.click()
  } finally {
    URL.revokeObjectURL(objectUrl)
  }
}
