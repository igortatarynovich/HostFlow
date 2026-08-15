import { api } from './client'

export type FormsPlatformHandler = {
  handler_id: string
  module_owner?: string | null
  creates?: string[]
  creates_on_create?: Record<string, boolean>
  route_intent?: string | null
}

export type FormsPlatformHandlersResponse = {
  handlers: FormsPlatformHandler[]
}

/** Forms public contract — registered destination handlers. Not Builder / P3. */
export async function listFormsPlatformHandlers(): Promise<FormsPlatformHandler[]> {
  const { data } = await api.get<FormsPlatformHandlersResponse>('/platform/forms/handlers')
  return Array.isArray(data?.handlers) ? data.handlers : []
}
