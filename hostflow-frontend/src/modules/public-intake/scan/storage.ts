import type { ScanQualityReport } from './analyzer'
import type { ProcessedFrameMeta } from './frameProcessor'

export type StoredScanPage = {
  id: string
  dataUrl: string
  name: string
  type: string
  createdAt: number
  quality?: ScanQualityReport
  width?: number
  height?: number
  preset?: string
  stepKey?: string | null
  pageIndex?: number
  meta?: ProcessedFrameMeta | null
}

export type ScanDraftSnapshot = {
  pages: StoredScanPage[]
  comment?: string
}

const DB_NAME = 'hostflow-scan-drafts'
const STORE_NAME = 'sessions'

let dbPromise: Promise<IDBDatabase | null> | undefined

function openDb(): Promise<IDBDatabase | null> {
  if (typeof window === 'undefined' || typeof window.indexedDB === 'undefined') {
    return Promise.resolve(null)
  }
  if (!dbPromise) {
    dbPromise = new Promise<IDBDatabase>((resolve, reject) => {
      const request = window.indexedDB.open(DB_NAME, 1)
      request.onerror = () => reject(request.error ?? new Error('Failed to open IndexedDB'))
      request.onupgradeneeded = () => {
        const db = request.result
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'token' })
        }
      }
      request.onsuccess = () => resolve(request.result)
    })
      .then<IDBDatabase | null>((db) => db)
      .catch((err) => {
        console.warn('scan storage: IndexedDB unavailable', err)
        return null
      })
  }
  return dbPromise
}

export async function saveScanDraft(token: string, snapshot: ScanDraftSnapshot): Promise<void> {
  const db = await openDb()
  if (!db) return
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    store.put({
      token,
      updated_at: Date.now(),
      pages: snapshot.pages,
      comment: snapshot.comment ?? '',
    })
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error || new Error('Failed to persist scan draft'))
    tx.onabort = () => reject(tx.error || new Error('Failed to persist scan draft'))
  })
}

export async function loadScanDraft(token: string): Promise<ScanDraftSnapshot | null> {
  const db = await openDb()
  if (!db) return null
  return await new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const request = store.get(token)
    request.onsuccess = () => {
      const result = request.result
      if (!result) {
        resolve(null)
        return
      }
      resolve({
        pages: result.pages ?? [],
        comment: result.comment ?? '',
      })
    }
    request.onerror = () => reject(request.error || new Error('Failed to read scan draft'))
  })
}

export async function clearScanDraft(token: string): Promise<void> {
  const db = await openDb()
  if (!db) return
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    store.delete(token)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error || new Error('Failed to clear scan draft'))
    tx.onabort = () => reject(tx.error || new Error('Failed to clear scan draft'))
  })
}
