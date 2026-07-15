import { useEffect, useState } from 'react'
import http from '../api/http'
import type { Option } from '../components/controls/Select'

type DialCodeOptionResponse = {
  value: string
  label: string
  meta?: { country?: string; name?: string }
}

let cachedOptions: Option[] | null = null
let inflight: Promise<Option[]> | null = null

async function fetchDialCodeOptions(): Promise<Option[]> {
  if (cachedOptions) return cachedOptions
  if (inflight) return inflight
  inflight = http
    .get<DialCodeOptionResponse[]>('/catalogs/dial-codes/options')
    .then(({ data }) => {
      cachedOptions = (data ?? [])
        .map((item) => ({
          value: String(item.value || '').trim(),
          label: String(item.label || item.value || '').trim(),
        }))
        .filter((item) => item.value && item.label)
      return cachedOptions
    })
    .finally(() => {
      inflight = null
    })
  return inflight
}

export function useDialCodeOptions() {
  const [options, setOptions] = useState<Option[]>(cachedOptions ?? [])
  const [loading, setLoading] = useState(!cachedOptions)

  useEffect(() => {
    let cancelled = false
    void fetchDialCodeOptions()
      .then((opts) => {
        if (!cancelled) {
          setOptions(opts)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { options, loading }
}

export function resolveDialCodeValue(value: string | null | undefined, options: Option[]): string {
  const trimmed = String(value || '').trim()
  if (trimmed && options.some((opt) => opt.value === trimmed)) return trimmed
  if (options.some((opt) => opt.value === '+48')) return '+48'
  return options[0]?.value ?? '+48'
}
