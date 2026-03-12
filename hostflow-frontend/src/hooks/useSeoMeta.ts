import { useEffect } from 'react'

type SeoMetaOptions = {
  title: string
  description: string
  canonicalPath: string
  ogType?: 'website' | 'article'
}

const DEFAULT_BASE_URL = 'https://hostflow.cc'

function normalizeBaseUrl(raw: string | undefined): string {
  const value = String(raw || '').trim().replace(/\/+$/, '')
  return value || DEFAULT_BASE_URL
}

function toAbsoluteUrl(baseUrl: string, path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${baseUrl}${normalizedPath}`
}

function upsertMeta(query: string, attrs: Record<string, string>) {
  let node = document.head.querySelector(`meta[${query}]`) as HTMLMetaElement | null
  if (!node) {
    node = document.createElement('meta')
    node.setAttribute('data-hf-seo', '1')
    document.head.appendChild(node)
  }
  Object.entries(attrs).forEach(([key, value]) => node!.setAttribute(key, value))
}

function upsertCanonical(href: string) {
  let node = document.head.querySelector('link[rel="canonical"]') as HTMLLinkElement | null
  if (!node) {
    node = document.createElement('link')
    node.setAttribute('rel', 'canonical')
    node.setAttribute('data-hf-seo', '1')
    document.head.appendChild(node)
  }
  node.setAttribute('href', href)
}

export function useSeoMeta({ title, description, canonicalPath, ogType = 'website' }: SeoMetaOptions) {
  useEffect(() => {
    if (typeof document === 'undefined') return

    const baseUrl = normalizeBaseUrl(import.meta.env.VITE_PUBLIC_BASE_URL as string | undefined)
    const canonicalUrl = toAbsoluteUrl(baseUrl, canonicalPath)
    const fullTitle = `${title} | HostFlow`

    document.title = fullTitle
    upsertCanonical(canonicalUrl)
    upsertMeta('name="description"', { name: 'description', content: description })
    upsertMeta('property="og:title"', { property: 'og:title', content: fullTitle })
    upsertMeta('property="og:description"', { property: 'og:description', content: description })
    upsertMeta('property="og:type"', { property: 'og:type', content: ogType })
    upsertMeta('property="og:url"', { property: 'og:url', content: canonicalUrl })
    upsertMeta('property="og:site_name"', { property: 'og:site_name', content: 'HostFlow' })
  }, [canonicalPath, description, ogType, title])
}
