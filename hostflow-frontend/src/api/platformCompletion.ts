import { api } from './client'

export type PlatformCompletionBlock = {
  title: string
  message: string
  action_label?: string | null
  client_id?: string | null
}

export type PlatformHandoff = {
  action: string
  label: string
  hint?: string | null
  context: Record<string, unknown>
}

export type PlatformCompletionResolution = {
  event: string
  completion: PlatformCompletionBlock
  handoff?: PlatformHandoff | null
  handoffs?: PlatformHandoff[]
  done?: PlatformCompletionBlock | null
}

export async function resolvePlatformCompletion(payload: {
  event: string
  context?: Record<string, unknown>
}): Promise<PlatformCompletionResolution> {
  const { data } = await api.post<PlatformCompletionResolution>('/platform/completion/resolve', payload)
  return data
}
