import { useCallback, useEffect, useMemo, useState } from 'react'

import type {
  AdditionalService,
  AdditionalServiceOrder,
  AdditionalServiceOrderSummary,
} from '../api/types'
import {
  getServiceOrder,
  getServiceOrderSummary,
  listAdditionalServices,
  listServiceOrders,
  type ServiceOrderQuery,
} from '../api/additionalServices'

export function useAdditionalServiceCatalog(includeInactive = false, includeMetrics = true) {
  const [services, setServices] = useState<AdditionalService[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listAdditionalServices(includeInactive, includeMetrics)
      setServices(data)
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [includeInactive, includeMetrics])

  useEffect(() => {
    void load()
  }, [load])

  return { services, loading, error, reload: load }
}

export function useServiceOrders(query: ServiceOrderQuery = {}) {
  const [orders, setOrders] = useState<AdditionalServiceOrder[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const key = useMemo(() => JSON.stringify(query ?? {}), [query])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const parsed: ServiceOrderQuery = key ? JSON.parse(key) : {}
      const data = await listServiceOrders(parsed)
      setOrders(data)
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [key])

  useEffect(() => {
    void load()
  }, [load])

  return { orders, loading, error, reload: load }
}

export function useServiceOrder(orderId: string | null | undefined) {
  const [order, setOrder] = useState<AdditionalServiceOrder | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const load = useCallback(async () => {
    if (!orderId) {
      setOrder(null)
      return
    }
    setLoading(true)
    try {
      const data = await getServiceOrder(orderId)
      setOrder(data)
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [orderId])

  useEffect(() => {
    void load()
  }, [load])

  return { order, loading, error, reload: load }
}

export function useServiceOrderSummary(orderId: string | null | undefined) {
  const [summary, setSummary] = useState<AdditionalServiceOrderSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const load = useCallback(async () => {
    if (!orderId) {
      setSummary(null)
      return
    }
    setLoading(true)
    try {
      const data = await getServiceOrderSummary(orderId)
      setSummary(data)
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [orderId])

  useEffect(() => {
    void load()
  }, [load])

  return { summary, loading, error, reload: load }
}
