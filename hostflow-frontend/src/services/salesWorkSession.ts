import { clientAcquisitionInquiryPath } from '../app/clientAcquisitionPaths'
import { salesInquiryPath, parseSalesHomeInquiryLeadId } from '../app/salesPaths'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

const STORAGE_KEY = 'hf:sales-work-session'

export type SalesWorkKind = 'call' | 'convert'

/**
 * Which work surface the one-by-one queue runs on:
 * - 'sales'       → company inquiries (Sales workspace + client-acquisition channels)
 * - 'recruitment' → candidate applications (full-page Lead detail = recruitment intake)
 */
export type WorkSessionSurface = 'sales' | 'recruitment'

export type SalesWorkSession = {
  /** Optional: set for channel-scoped sessions; empty for the general Sales entry. */
  channelId?: string
  /** Defaults to 'sales' for backward compatibility. */
  surface?: WorkSessionSurface
  kind: SalesWorkKind | string
  queue: string[]
  index: number
  returnPath: string
}

function readRaw(): SalesWorkSession | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as SalesWorkSession
    if (!Array.isArray(parsed?.queue) || parsed.queue.length === 0) return null
    return parsed
  } catch {
    return null
  }
}

function write(session: SalesWorkSession | null) {
  if (typeof window === 'undefined') return
  try {
    if (!session) window.sessionStorage.removeItem(STORAGE_KEY)
    else window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  } catch {
    /* ignore */
  }
}

export function getSalesWorkSession(): SalesWorkSession | null {
  return readRaw()
}

export function startSalesWorkSession(input: {
  channelId?: string
  surface?: WorkSessionSurface
  kind: SalesWorkKind | string
  queue: string[]
  returnPath: string
}): SalesWorkSession {
  const session: SalesWorkSession = {
    channelId: input.channelId,
    surface: input.surface ?? 'sales',
    kind: input.kind,
    queue: input.queue.filter(Boolean),
    index: 0,
    returnPath: input.returnPath,
  }
  write(session)
  return session
}

export function advanceSalesWorkSession(): string | null {
  const session = readRaw()
  if (!session) return null
  const nextIndex = session.index + 1
  if (nextIndex >= session.queue.length) {
    write(null)
    return null
  }
  const updated = { ...session, index: nextIndex }
  write(updated)
  return updated.queue[nextIndex] ?? null
}

export function cancelSalesWorkSession() {
  write(null)
}

export function leadHref(leadId: string, channelId?: string): string {
  const session = getSalesWorkSession()
  // Candidate applications are worked on the full-page Lead detail (recruitment intake).
  if (session?.surface === 'recruitment') {
    return `${CRM_APP_PATHS.leads}/${encodeURIComponent(leadId)}`
  }
  const resolvedChannel = channelId || session?.channelId
  if (resolvedChannel) {
    return clientAcquisitionInquiryPath(resolvedChannel, leadId)
  }
  return salesInquiryPath(leadId)
}

export function parseSalesInquiryLeadId(pathname: string): string | null {
  const fromHome = parseSalesHomeInquiryLeadId(pathname)
  if (fromHome) return fromHome
  const marker = '/client-acquisition/channels/'
  const idx = pathname.indexOf(marker)
  if (idx < 0) return null
  const rest = pathname.slice(idx + marker.length)
  const parts = rest.split('/')
  if (parts.length >= 3 && parts[1] === 'inquiries' && parts[2]) {
    return parts[2].split('?')[0] || null
  }
  return null
}

export function isActiveWorkSessionForLead(leadId: string): boolean {
  const session = getSalesWorkSession()
  if (!session) return false
  return session.queue[session.index] === leadId
}
