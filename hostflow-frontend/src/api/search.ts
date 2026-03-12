import { api, docsApi } from './client'
import type { Candidate, Company, Document } from './types'

export type GlobalSearchResult = {
  type: 'candidate' | 'company' | 'document'
  id: string
  title: string
  subtitle?: string
  link: string
}

function asArray<T = any>(value: any): T[] {
  if (!value) return []
  if (Array.isArray(value)) return value
  if (Array.isArray(value?.items)) return value.items
  if (Array.isArray(value?.data)) return value.data
  return []
}

const MIN_SEARCH_LENGTH = 2

export async function searchGlobal(query: string, signal?: AbortSignal): Promise<GlobalSearchResult[]> {
  const q = query.trim()
  if (!q || q.length < MIN_SEARCH_LENGTH) return []
  const params = { q, limit: 5, offset: 0 }
  const [candidates, companies, documents] = await Promise.allSettled([
    api.get('/candidates/', { params, signal }),
    api.get('/companies/', { params, signal }),
    docsApi.get('/documents', { params: { q, limit: 5 }, signal }),
  ])

  const results: GlobalSearchResult[] = []

  if (candidates.status === 'fulfilled') {
    asArray<Candidate>(candidates.value.data).forEach((item) => {
      if (!item?.id) return
      const title = `${item.first_name ?? ''} ${item.last_name ?? ''}`.trim() || item.email || item.short_id || 'Кандидат'
      results.push({
        type: 'candidate',
        id: item.id,
        title,
        subtitle: item.stage || item.email || undefined,
        link: `/app/candidates/${item.id}`,
      })
    })
  }

  if (companies.status === 'fulfilled') {
    asArray<Company>(companies.value.data).forEach((item) => {
      if (!item?.id) return
      results.push({
        type: 'company',
        id: item.id,
        title: item.name || item.legal_name || 'Компания',
        subtitle: item.city || item.country_code || undefined,
        link: `/app/clients/${item.id}`,
      })
    })
  }

  if (documents.status === 'fulfilled') {
    asArray<Document>(documents.value.data).forEach((doc) => {
      if (!doc?.id) return
      const ownerId = doc.candidate_id || doc.owner_id
      results.push({
        type: 'document',
        id: doc.id,
        title: doc.title || doc.custom_name || doc.doc_type || 'Документ',
        subtitle: doc.status ? `Статус: ${doc.status}` : undefined,
        link: ownerId ? `/app/candidates/${ownerId}/documents` : '/app/documents',
      })
    })
  }

  return results.slice(0, 15)
}
